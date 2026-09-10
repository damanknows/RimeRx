import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Path definitions
BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
STATIC_DIR = BASE_DIR / "static"
AUDIO_DIR = STATIC_DIR / "audio"
CONFIG_DIR = BASE_DIR / "config"
CORPUS_DIR = BASE_DIR / "corpus"
RESULTS_DIR = BASE_DIR / "results"

# Ensure essential directories exist
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Server Configuration (Render compatibility)
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")

# API Keys
RIME_API_KEY = os.getenv("RIME_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# Key validation placeholders
PLACEHOLDER_KEYS = {"", "your_rime_api_key_here", "your_openai_api_key_here", "your_elevenlabs_api_key_here"}

def is_rime_key_configured() -> bool:
    """Returns True if a non-placeholder Rime API key is set."""
    return bool(RIME_API_KEY and RIME_API_KEY not in PLACEHOLDER_KEYS)

def is_openai_key_configured() -> bool:
    """Returns True if a non-placeholder OpenAI API key is set."""
    return bool(OPENAI_API_KEY and OPENAI_API_KEY not in PLACEHOLDER_KEYS)

def is_elevenlabs_key_configured() -> bool:
    """Returns True if a non-placeholder ElevenLabs API key is set."""
    return bool(ELEVENLABS_API_KEY and ELEVENLABS_API_KEY not in PLACEHOLDER_KEYS)
