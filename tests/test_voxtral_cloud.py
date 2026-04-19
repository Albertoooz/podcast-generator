from __future__ import annotations

import base64

import httpx
import pytest

from app.tts.providers.voxtral_cloud import (
    _decode_response_body,
    _filter_speech_options,
    _is_mistral_voice_uuid,
    _mistral_api_root,
    _mistral_audio_speech_url,
    _mistral_voices_url,
    _normalize_cloud_model,
    _speech_model_for_api,
)


def test_decode_json_audio_data():
    raw = b"\xff\xfb\x90"
    b64 = base64.standard_b64encode(raw).decode("ascii")
    r = httpx.Response(200, json={"audio_data": b64})
    assert _decode_response_body(r) == raw


def test_decode_raw_bytes():
    raw = b"ID3fake"
    r = httpx.Response(200, content=raw, headers={"content-type": "audio/mpeg"})
    assert _decode_response_body(r) == raw


def test_mistral_audio_speech_url_variants():
    assert _mistral_audio_speech_url("https://api.mistral.ai/v1") == (
        "https://api.mistral.ai/v1/audio/speech"
    )
    assert _mistral_audio_speech_url("https://api.mistral.ai") == (
        "https://api.mistral.ai/v1/audio/speech"
    )
    assert _mistral_audio_speech_url("https://api.mistral.ai/") == (
        "https://api.mistral.ai/v1/audio/speech"
    )
    full = "https://api.mistral.ai/v1/audio/speech"
    assert _mistral_audio_speech_url(full) == full
    assert _mistral_audio_speech_url(full + "/") == full


def test_is_mistral_voice_uuid():
    assert _is_mistral_voice_uuid("a3e8f2b1-4c9d-4a6b-8e2f-1c3d5e7a9b0c")
    assert not _is_mistral_voice_uuid("casual_male")
    assert not _is_mistral_voice_uuid("cheerful_female")
    assert not _is_mistral_voice_uuid("mistral_default")
    assert not _is_mistral_voice_uuid("")


def test_normalize_cloud_model_aliases_legacy():
    assert _normalize_cloud_model("voxtral-tts-2603") == "voxtral-mini-tts-2603"
    assert _normalize_cloud_model(None) == "voxtral-mini-tts-2603"
    assert _normalize_cloud_model("  ") == "voxtral-mini-tts-2603"
    assert _normalize_cloud_model("custom-tts") == "custom-tts"


def test_mistral_voices_url_variants():
    base = "https://api.mistral.ai/v1"
    assert _mistral_voices_url(base) == "https://api.mistral.ai/v1/audio/voices"
    assert _mistral_voices_url("https://api.mistral.ai") == "https://api.mistral.ai/v1/audio/voices"
    # Full speech URL → strip and build voices URL
    assert _mistral_voices_url("https://api.mistral.ai/v1/audio/speech") == (
        "https://api.mistral.ai/v1/audio/voices"
    )
    # With voice_id
    assert _mistral_voices_url(base, voice_id="abc-123") == (
        "https://api.mistral.ai/v1/audio/voices/abc-123"
    )


def test_mistral_api_root():
    assert _mistral_api_root("https://api.mistral.ai/v1") == "https://api.mistral.ai/v1"
    assert _mistral_api_root("https://api.mistral.ai") == "https://api.mistral.ai/v1"
    assert _mistral_api_root("https://api.mistral.ai/v1/audio/speech") == (
        "https://api.mistral.ai/v1"
    )
    assert _mistral_api_root("https://api.mistral.ai/v1/audio/voices") == (
        "https://api.mistral.ai/v1"
    )


def test_decode_json_missing_audio_data():
    r = httpx.Response(200, json={"error": "no"})
    with pytest.raises(ValueError, match="Unexpected JSON"):
        _decode_response_body(r)


def test_filter_speech_options_drops_unknown():
    raw = {"voice": "x", "temperature": 0.7, "max_tokens": 99, "foo": 1}
    assert _filter_speech_options(raw) == {"voice": "x"}


def test_speech_model_for_api_rejects_non_voxtral():
    assert _speech_model_for_api("gpt-4o-mini-tts") == "voxtral-mini-tts-2603"


def test_speech_model_for_api_keeps_voxtral():
    assert _speech_model_for_api("voxtral-mini-tts-2603") == "voxtral-mini-tts-2603"
