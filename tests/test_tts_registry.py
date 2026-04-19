from __future__ import annotations

import pytest

from app.tts.registry import get_tts_provider, list_tts_provider_ids


def test_list_tts_provider_ids():
    ids = list_tts_provider_ids()
    assert "openai" in ids
    assert "elevenlabs" in ids


def test_registry_openai():
    p = get_tts_provider("openai")
    assert p.name == "openai"


def test_registry_voxtral_mlx():
    p = get_tts_provider("voxtral_mlx")
    assert p.name == "voxtral_mlx"


def test_registry_unknown():
    with pytest.raises(ValueError):
        get_tts_provider("not_a_provider")
