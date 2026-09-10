import os

_raw_model = os.getenv("RIME_MODEL")
RIME_MODEL = _raw_model if _raw_model and not _raw_model.startswith("your_") else "mistv3"

_raw_speaker = os.getenv("RIME_SPEAKER")
RIME_SPEAKER = _raw_speaker if _raw_speaker and not _raw_speaker.startswith("your_") else "sirius"

_raw_lang = os.getenv("RIME_LANGUAGE")
RIME_LANGUAGE = _raw_lang if _raw_lang and not _raw_lang.startswith("your_") else "en-IN"

_raw_endpoint = os.getenv("RIME_ENDPOINT") or os.getenv("RIME_URL")
RIME_ENDPOINT = _raw_endpoint if _raw_endpoint and not _raw_endpoint.startswith("your_") else "https://users.rime.ai/v1/rime-tts"

_raw_format = os.getenv("RIME_AUDIO_FORMAT")
RIME_AUDIO_FORMAT = _raw_format if _raw_format and not _raw_format.startswith("your_") else "mp3"

_raw_ws_endpoint = os.getenv("RIME_WS_ENDPOINT")
RIME_WS_ENDPOINT = _raw_ws_endpoint if _raw_ws_endpoint and not _raw_ws_endpoint.startswith("your_") else "wss://users-ws.rime.ai/ws3"


def verify_rime_configuration(
    api_key: str | None = None,
    model: str = RIME_MODEL,
    speaker: str = RIME_SPEAKER,
    lang: str = RIME_LANGUAGE,
    endpoint: str = RIME_ENDPOINT,
    audio_format: str = RIME_AUDIO_FORMAT,
    raise_on_failure: bool = True,
) -> tuple[bool, str]:
    """Verify configured model, speaker, and language against Rime's live catalog.

    Queries Rime's production API to confirm that the model, speaker, and language
    combination is currently valid and active in Rime's live catalog.
    If the combination is invalid or rejected, fails loudly with [CONFIG ERROR].

    Returns:
        (is_valid, message): Boolean validation status and diagnostic message.
    """
    import httpx

    resolved_key = api_key or os.getenv("RIME_API_KEY", "").strip()
    if not resolved_key or resolved_key.startswith("your_"):
        msg = "[CONFIG ERROR] RIME_API_KEY is not configured or is a placeholder."
        if raise_on_failure:
            raise ValueError(msg)
        return False, msg

    # Probe Rime TTS endpoint with minimal text payload to validate catalog combination
    headers = {
        "Authorization": f"Bearer {resolved_key}",
        "Content-Type": "application/json",
        "Accept": f"audio/{audio_format}",
    }
    payload = {
        "speaker": speaker,
        "modelId": model,
        "text": ".",
        "lang": lang,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(endpoint, json=payload, headers=headers)
    except Exception as exc:
        msg = f"[CONFIG ERROR] Could not connect to Rime endpoint '{endpoint}': {exc}"
        if raise_on_failure:
            raise RuntimeError(msg) from exc
        return False, msg

    if resp.status_code == 200 and len(resp.content) > 0:
        msg = f"[CONFIG OK] Verified live Rime catalog combination: model='{model}', speaker='{speaker}', lang='{lang}'"
        return True, msg

    # Non-200 means Rime rejected the combination
    error_detail = resp.text.strip()
    msg = (
        f"[CONFIG ERROR] Rime live catalog rejected configuration! "
        f"model='{model}', speaker='{speaker}', lang='{lang}' (HTTP {resp.status_code}): {error_detail}"
    )
    if raise_on_failure:
        raise ValueError(msg)
    return False, msg

