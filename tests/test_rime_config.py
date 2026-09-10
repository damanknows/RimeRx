""""Tests for Rime live production catalog verification and loud failure mechanics."""

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from dotenv import load_dotenv

from config.rime import (
    RIME_AUDIO_FORMAT,
    RIME_ENDPOINT,
    RIME_LANGUAGE,
    RIME_MODEL,
    RIME_SPEAKER,
    verify_rime_configuration,
)

load_dotenv()


def test_valid_rime_production_configuration():
    """Ensure current config (mistv3, sirius, en-IN) is valid against Rime's live production catalog."""
    api_key = os.getenv("RIME_API_KEY")
    if not api_key:
        pytest.skip("RIME_API_KEY is not configured in environment.")

    is_valid, msg = verify_rime_configuration(
        api_key=api_key,
        model=RIME_MODEL,
        speaker=RIME_SPEAKER,
        lang=RIME_LANGUAGE,
        endpoint=RIME_ENDPOINT,
        audio_format=RIME_AUDIO_FORMAT,
        raise_on_failure=False,
    )
    assert is_valid is True, f"Config validation unexpectedly failed: {msg}"
    assert "[CONFIG OK]" in msg


def test_invalid_speaker_fails_loudly():
    """Ensure an invalid speaker fails loudly with [CONFIG ERROR] and raises ValueError."""
    api_key = os.getenv("RIME_API_KEY")
    if not api_key:
        pytest.skip("RIME_API_KEY is not configured in environment.")

    with pytest.raises(ValueError, match="CONFIG ERROR"):
        verify_rime_configuration(
            api_key=api_key,
            model="mistv3",
            speaker="non_existent_speaker_xyz",
            lang="en-IN",
            raise_on_failure=True,
        )


def test_invalid_language_fails_loudly():
    """Ensure an unsupported language fails loudly with [CONFIG ERROR] and raises ValueError."""
    api_key = os.getenv("RIME_API_KEY")
    if not api_key:
        pytest.skip("RIME_API_KEY is not configured in environment.")

    with pytest.raises(ValueError, match="CONFIG ERROR"):
        verify_rime_configuration(
            api_key=api_key,
            model="mistv3",
            speaker="sirius",
            lang="invalid-lang-code",
            raise_on_failure=True,
        )

