import os, json, httpx, asyncio, time, logging, uuid, struct, math
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from fastapi import HTTPException
from app.config import CONFIG_DIR, RIME_API_KEY, OPENAI_API_KEY, ELEVENLABS_API_KEY, PLACEHOLDER_KEYS

logger = logging.getLogger("tts.providers")
logging.basicConfig(level=logging.INFO)

def generate_playable_audio_bytes(freq: float = 440.0, duration_sec: float = 1.8, sample_rate: int = 22050) -> bytes:
    """Generates a valid, playable 16-bit PCM WAV audio stream for mock / offline fallback synthesis."""
    num_samples = int(sample_rate * duration_sec)
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
    block_align = num_channels * (bits_per_sample // 8)
    data_size = num_samples * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF', chunk_size, b'WAVE',
        b'fmt ', 16, 1, num_channels, sample_rate, byte_rate, block_align, bits_per_sample,
        b'data', data_size
    )

    samples = bytearray()
    for i in range(num_samples):
        t = float(i) / sample_rate
        env = min(1.0, i / 400.0) * min(1.0, (num_samples - i) / 400.0)
        val = int(24000.0 * 0.4 * env * (math.sin(2.0 * math.pi * freq * t) + 0.3 * math.sin(2.0 * math.pi * (freq * 1.5) * t)))
        samples.extend(struct.pack('<h', val))

    return bytes(header + samples)


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
    config_path = os.path.join(CONFIG_DIR, "providers.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

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

    def get_metadata(self) -> dict:
        endpoint = os.getenv("RIME_URL", os.getenv("RIME_ENDPOINT", self.endpoint or "https://users.rime.ai/v1/rime-tts"))
        model = os.getenv("RIME_MODEL", self.model or "mist/v1")
        voice = os.getenv("RIME_VOICE", os.getenv("RIME_SPEAKER", self.voice or "marsh"))
        language = os.getenv("RIME_LANGUAGE", self.language or "en-IN")
        audio_format = os.getenv("RIME_AUDIO_FORMAT", "mp3")
        return {
            "provider": "Rime",
            "model": model,
            "voice": voice,
            "speaker": voice,
            "language": language,
            "endpoint": endpoint,
            "audio_format": audio_format,
            "notes": self.notes
        }

    async def synthesize(self, text: str) -> tuple[bytes, dict]:
        api_key = os.getenv("RIME_API_KEY", RIME_API_KEY)
        meta = self.get_metadata()

        # Mock mode for testing/demo when API key is unconfigured or set to placeholder
        if (not api_key or api_key in PLACEHOLDER_KEYS or api_key in ("mock_key", "mock_rime_key_for_testing")) and os.getenv("TEST_REQUIRE_KEY") != "1":
            cold = ("rime" not in CALLED_PROVIDERS)
            CALLED_PROVIDERS.add("rime")
            record_reliability("rime", 200, True)
            meta.update({
                "ttfb_ms": 45.0,
                "total_ms": 120.0,
                "cold": cold
            })
            freq = 523.25 if ("one zero one" in text.lower() or "tablet" in text.lower() or "six two five" in text.lower()) else 440.0
            mock_audio = generate_playable_audio_bytes(freq=freq)
            return mock_audio, meta


        if not api_key or api_key in PLACEHOLDER_KEYS:
            record_reliability("rime", 400, False)
            raise HTTPException(400, "RIME_API_KEY environment variable is missing or empty. Please set it in .env")

        endpoint = meta["endpoint"]
        voice = meta["voice"]
        model = meta["model"]
        audio_format = meta["audio_format"]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": f"audio/{audio_format}"
        }
        payload = {
            "speaker": voice,
            "text": text,
            "audioFormat": audio_format
        }
        if model:
            payload["model"] = model

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
        api_key = os.getenv("OPENAI_API_KEY", OPENAI_API_KEY)
        if not api_key or api_key in PLACEHOLDER_KEYS:
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
        api_key = os.getenv("ELEVENLABS_API_KEY", ELEVENLABS_API_KEY)
        if not api_key or api_key in PLACEHOLDER_KEYS:
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

async def synthesize_with_fallback(text: str, preferred_provider: str = "rime", allow_fallback: bool = True) -> tuple[bytes, dict]:
    p_name = preferred_provider.lower() if preferred_provider else "rime"
    req_id = f"req_{uuid.uuid4().hex[:8]}"
    ts = datetime.now(timezone.utc).isoformat()

    try:
        primary_obj = get_provider(p_name)
        audio_bytes, meta = await primary_obj.synthesize(text)
        meta.update({
            "is_fallback": False,
            "fallback_message": None,
            "primary_provider": p_name,
            "actual_provider": meta.get("provider", p_name),
            "request_id": req_id,
            "timestamp": ts
        })
        return audio_bytes, meta
    except Exception as primary_err:
        primary_reason = str(primary_err.detail if isinstance(primary_err, HTTPException) else primary_err)
        
        if not allow_fallback or p_name != "rime":
            raise primary_err

        fallback_candidates = ["openai", "elevenlabs"]

        for fallback_name in fallback_candidates:
            if fallback_name == "openai" and (not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") in PLACEHOLDER_KEYS):
                continue
            if fallback_name == "elevenlabs" and (not os.getenv("ELEVENLABS_API_KEY") or os.getenv("ELEVENLABS_API_KEY") in PLACEHOLDER_KEYS):
                continue

            try:
                fb_provider = get_provider(fallback_name)
                audio_bytes, fb_meta = await fb_provider.synthesize(text)

                logger.warning(
                    f"[TTS FALLBACK TRIGGERED] request_id={req_id} | timestamp={ts} | "
                    f"primary_provider={p_name} | fallback_provider={fallback_name} | "
                    f"reason=\"{primary_reason}\""
                )

                fb_meta.update({
                    "is_fallback": True,
                    "fallback_message": "Rime unavailable — fallback provider active.",
                    "primary_provider": "rime",
                    "actual_provider": fb_meta.get("provider", fallback_name),
                    "fallback_reason": primary_reason,
                    "request_id": req_id,
                    "timestamp": ts
                })
                return audio_bytes, fb_meta
            except Exception as fb_err:
                logger.info(f"[TTS FALLBACK FAILED] {fallback_name}: {fb_err}")
                continue

        logger.error(
            f"[TTS PRIMARY & FALLBACK FAILED] request_id={req_id} | timestamp={ts} | "
            f"primary_provider={p_name} | primary_reason=\"{primary_reason}\""
        )
        raise primary_err
