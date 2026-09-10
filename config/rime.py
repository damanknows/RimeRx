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

