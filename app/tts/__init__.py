"""
Text-To-Speech Providers Package for RimeRx
"""
from app.tts.providers import get_provider, synthesize_with_fallback, PROVIDERS_CONFIG, RELIABILITY_STATS

__all__ = ["get_provider", "synthesize_with_fallback", "PROVIDERS_CONFIG", "RELIABILITY_STATS"]
