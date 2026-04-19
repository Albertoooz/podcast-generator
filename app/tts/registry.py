"""Resolve TTS provider name to implementation."""

from __future__ import annotations

from app.tts.base import TTSProvider
from app.tts.providers.elevenlabs import ElevenLabsProvider
from app.tts.providers.openai_tts import OpenAITTSProvider
from app.tts.providers.voxtral_cloud import VoxtralCloudProvider
from app.tts.providers.voxtral_local import VoxtralLocalProvider
from app.tts.providers.voxtral_mlx import VoxtralMLXProvider
from app.tts.providers.xtts import XTTSProvider

_REGISTRY: dict[str, type[TTSProvider]] = {
    "openai": OpenAITTSProvider,
    "elevenlabs": ElevenLabsProvider,
    "voxtral_cloud": VoxtralCloudProvider,
    "voxtral_local": VoxtralLocalProvider,
    "voxtral_mlx": VoxtralMLXProvider,
    "xtts": XTTSProvider,
}

_INSTANCES: dict[str, TTSProvider] = {}


def register_provider(name: str, cls: type[TTSProvider]) -> None:
    _REGISTRY[name.lower()] = cls


def list_tts_provider_ids() -> list[str]:
    """Registered TTS provider ids (lowercase)."""
    return sorted(_REGISTRY.keys())


def get_tts_provider(name: str) -> TTSProvider:
    key = name.lower().strip()
    if key not in _REGISTRY:
        raise ValueError(f"Unknown TTS provider: {name}. Known: {list(_REGISTRY)}")
    if key not in _INSTANCES:
        _INSTANCES[key] = _REGISTRY[key]()
    return _INSTANCES[key]
