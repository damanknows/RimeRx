import os, json, httpx, asyncio, time, logging
from abc import ABC, abstractmethod
from fastapi import HTTPException
from config.rime import RIME_MODEL, RIME_SPEAKER, RIME_LANGUAGE, RIME_ENDPOINT, RIME_AUDIO_FORMAT

logger = logging.getLogger("tts.providers")
logging.basicConfig(level=logging.INFO)

CALLED_PROVIDERS = set()
RELIABILITY_STATS = {
    "rime": {"total_calls": 0, "successes": 0, "failures": 0, "status_codes": {}},
    "openai": {"total_calls": 0, "successes": 0, "failures": 0, "status_codes": {}},
    "elevenlabs": {"total_calls": 0, "successes": 0, "failures": 0, "status_codes": {}},
}

def record_reliability(provider: str, status_code: int, is_success: bool):
    p = provider.lower()
    if p not in RELIABILITY_STATS:
        RELIABILITY_STATS[p] = {"total_calls": 0, "successes": 0, "failures": 0, "status_codes": {}}
    st = RELIABILITY_STATS[p]
    st["total_calls"] += 1
    if is_success:
        st["successes"] += 1
    else:
        st["failures"] += 1
    code_str = str(status_code)
    st["status_codes"][code_str] = st["status_codes"].get(code_str, 0) + 1

def load_providers_config() -> dict:
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "providers.json")
    cfg = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    if "rime" not in cfg:
        cfg["rime"] = {}
    cfg["rime"]["model"] = RIME_MODEL
    cfg["rime"]["voice"] = RIME_SPEAKER
    cfg["rime"]["endpoint"] = RIME_ENDPOINT
    cfg["rime"]["language"] = RIME_LANGUAGE
    return cfg

PROVIDERS_CONFIG = load_providers_config()

class TTSProvider(ABC):
    def __init__(self, provider_name: str, config: dict):
        self.provider_name = provider_name
        self.model = config.get("model", "")
        self.voice = config.get("voice", "")
        self.endpoint = config.get("endpoint", "")
        self.language = config.get("language", "en-US")
        self.notes = config.get("notes", "")

    @abstractmethod
    async def synthesize(self, text: str) -> tuple[bytes, dict]:
        """Synthesizes text to audio bytes and returns (audio_bytes, metadata_dict)."""
        pass

    def get_metadata(self) -> dict:
        return {
            "provider": self.provider_name,
            "model": self.model,
            "voice": self.voice,
            "language": self.language,
            "notes": self.notes
        }

class RimeProvider(TTSProvider):
    def __init__(self, config: dict):
        super().__init__("rime", config)
        self.model = self.model or RIME_MODEL
        self.voice = self.voice or RIME_SPEAKER
        self.language = self.language or RIME_LANGUAGE
        self.endpoint = self.endpoint or RIME_ENDPOINT

    async def synthesize(self, text: str) -> tuple[bytes, dict]:
        api_key = os.getenv("RIME_API_KEY")
        if not api_key:
            record_reliability("rime", 400, False)
            raise HTTPException(400, "RIME_API_KEY environment variable is missing or empty. Please set it in .env")

        endpoint = self.endpoint or RIME_ENDPOINT
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": f"audio/{RIME_AUDIO_FORMAT}"
        }
        payload = {
            "speaker": self.voice or RIME_SPEAKER,
            "text": text,
            "modelId": self.model or RIME_MODEL,
            "model": self.model or RIME_MODEL,
            "audioFormat": RIME_AUDIO_FORMAT
        }

        cold = ("rime" not in CALLED_PROVIDERS)
        CALLED_PROVIDERS.add("rime")
        logger.info(f"[RIME] {'COLD' if cold else 'WARM'} run starting...")

        last_error = None
        for attempt in range(2):
            try:
                start_time = time.perf_counter()
                async with httpx.AsyncClient(timeout=30.0) as client:
                    req = client.build_request("POST", endpoint, json=payload, headers=headers)
                    resp = await client.send(req, stream=True)
                    ttfb_ms = (time.perf_counter() - start_time) * 1000.0

                    if resp.status_code == 200:
                        content = await resp.aread()
                        await resp.aclose()
                        total_ms = (time.perf_counter() - start_time) * 1000.0
                        record_reliability("rime", 200, True)
                        meta = self.get_metadata()
                        meta.update({
                            "ttfb_ms": round(ttfb_ms, 2),
                            "total_ms": round(total_ms, 2),
                            "cold": cold
                        })
                        return content, meta
                    elif resp.status_code in (429, 500, 502, 503, 504):
                        err_text = (await resp.aread()).decode("utf-8", errors="ignore")[:150]
                        await resp.aclose()
                        record_reliability("rime", resp.status_code, False)
                        last_error = f"HTTP {resp.status_code}: {err_text}"
                        await asyncio.sleep(1.0)
                        continue
                    else:
                        err_text = (await resp.aread()).decode("utf-8", errors="ignore")[:200]
                        await resp.aclose()
                        record_reliability("rime", resp.status_code, False)
                        raise HTTPException(resp.status_code, f"Rime API Error ({resp.status_code}): {err_text}")
            except httpx.TimeoutException as e:
                record_reliability("rime", 408, False)
                last_error = f"Timeout: {e}"
                await asyncio.sleep(1.0)
            except HTTPException:
                raise
            except Exception as e:
                record_reliability("rime", 500, False)
                last_error = str(e)
                await asyncio.sleep(1.0)

        raise HTTPException(500, f"Rime API Failed after retries: {last_error}")

class OpenAIProvider(TTSProvider):
    def __init__(self, config: dict):
        super().__init__("openai", config)

    async def synthesize(self, text: str) -> tuple[bytes, dict]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your_openai_api_key_here":
            record_reliability("openai", 400, False)
            raise HTTPException(400, "OPENAI_API_KEY environment variable is missing or empty. Please set a valid key in .env")

        endpoint = self.endpoint or "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model or "tts-1",
            "input": text,
            "voice": self.voice or "alloy",
            "response_format": "mp3"
        }

        cold = ("openai" not in CALLED_PROVIDERS)
        CALLED_PROVIDERS.add("openai")
        logger.info(f"[OPENAI] {'COLD' if cold else 'WARM'} run starting...")

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                req = client.build_request("POST", endpoint, json=payload, headers=headers)
                resp = await client.send(req, stream=True)
                ttfb_ms = (time.perf_counter() - start_time) * 1000.0

                if resp.status_code == 200:
                    content = await resp.aread()
                    await resp.aclose()
                    total_ms = (time.perf_counter() - start_time) * 1000.0
                    record_reliability("openai", 200, True)
                    meta = self.get_metadata()
                    meta.update({
                        "ttfb_ms": round(ttfb_ms, 2),
                        "total_ms": round(total_ms, 2),
                        "cold": cold
                    })
                    return content, meta
                else:
                    err_text = (await resp.aread()).decode("utf-8", errors="ignore")[:200]
                    await resp.aclose()
                    record_reliability("openai", resp.status_code, False)
                    raise HTTPException(resp.status_code, f"OpenAI TTS API Error ({resp.status_code}): {err_text}")
        except HTTPException:
            raise
        except Exception as e:
            record_reliability("openai", 500, False)
            raise HTTPException(500, f"OpenAI TTS API Failed: {e}")

class ElevenLabsProvider(TTSProvider):
    def __init__(self, config: dict):
        super().__init__("elevenlabs", config)

    async def synthesize(self, text: str) -> tuple[bytes, dict]:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key or api_key == "your_elevenlabs_api_key_here":
            record_reliability("elevenlabs", 400, False)
            raise HTTPException(400, "ELEVENLABS_API_KEY environment variable is missing or empty. Please set a valid key in .env")

        voice_id = self.voice or "21m00Tcm4TlvDq8ikWAM"
        endpoint = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_22050_32"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        }
        payload = {
            "text": text,
            "model_id": self.model or "eleven_flash_v2_5"
        }

        cold = ("elevenlabs" not in CALLED_PROVIDERS)
        CALLED_PROVIDERS.add("elevenlabs")
        logger.info(f"[ELEVENLABS] {'COLD' if cold else 'WARM'} run starting...")

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                req = client.build_request("POST", endpoint, json=payload, headers=headers)
                resp = await client.send(req, stream=True)
                ttfb_ms = (time.perf_counter() - start_time) * 1000.0

                if resp.status_code == 200:
                    content = await resp.aread()
                    await resp.aclose()
                    total_ms = (time.perf_counter() - start_time) * 1000.0
                    record_reliability("elevenlabs", 200, True)
                    meta = self.get_metadata()
                    meta.update({
                        "ttfb_ms": round(ttfb_ms, 2),
                        "total_ms": round(total_ms, 2),
                        "cold": cold
                    })
                    return content, meta
                else:
                    err_text = (await resp.aread()).decode("utf-8", errors="ignore")[:200]
                    await resp.aclose()
                    record_reliability("elevenlabs", resp.status_code, False)
                    raise HTTPException(resp.status_code, f"ElevenLabs API Error ({resp.status_code}): {err_text}")
        except HTTPException:
            raise
        except Exception as e:
            record_reliability("elevenlabs", 500, False)
            raise HTTPException(500, f"ElevenLabs API Failed: {e}")

def get_provider(name: str = "rime") -> TTSProvider:
    name_lower = name.lower() if name else "rime"
    config_dict = PROVIDERS_CONFIG.get(name_lower, {})

    if name_lower == "rime":
        return RimeProvider(config_dict)
    elif name_lower == "openai":
        return OpenAIProvider(config_dict)
    elif name_lower == "elevenlabs":
        return ElevenLabsProvider(config_dict)
    else:
        raise HTTPException(400, f"Unknown TTS provider: '{name}'. Supported providers: 'rime', 'openai', 'elevenlabs'")
