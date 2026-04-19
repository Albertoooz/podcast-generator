from __future__ import annotations

import pytest

from app.tts import voice_library as vl


def test_add_list_voice(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    sample = tmp_path / "s.wav"
    sample.write_bytes(b"fake")
    vid = vl.add_voice(
        "Test voice",
        "voxtral_cloud",
        sample_path=sample,
        style_description="test",
        voice_id="v1",
    )
    assert vid == "v1"
    assert "v1" in vl.list_voices()
    meta = vl.get_voice("v1")
    assert meta is not None
    assert meta["style_description"] == "test"


def test_update_voice(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    sample = tmp_path / "a.wav"
    sample.write_bytes(b"x")
    vl.add_voice(
        "Vx",
        "voxtral_cloud",
        sample_path=sample,
        style_description="old",
        language="en",
        voice_id="vx",
    )
    assert vl.update_voice("vx", style_description="new")
    meta = vl.get_voice("vx")
    assert meta is not None
    assert meta["style_description"] == "new"
    assert meta["language"] == "en"
    assert vl.update_voice("vx", language="pl")
    assert vl.get_voice("vx")["language"] == "pl"
    assert vl.update_voice("vx", language="")
    assert vl.get_voice("vx")["language"] is None


def test_speaker_avatar_path_field():
    from app.models.speaker import Speaker

    s = Speaker(
        name="A",
        voice_id="v1",
        backstory="b",
        personality="p",
        avatar_path="/tmp/a.png",
    )
    assert s.avatar_path == "/tmp/a.png"
    s2 = Speaker(name="B", voice_id="v2", backstory="b", personality="p")
    assert s2.avatar_path is None


def test_voice_entry_validation(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    from app.tts import voice_library as vl

    with pytest.raises(Exception):
        vl.add_voice("bad", "elevenlabs", style_description="x", voice_id="e1")
    p = tmp_path / "s.wav"
    p.write_bytes(b"x")
    vid = vl.add_voice(
        "ok",
        "voxtral_cloud",
        provider_voice_id="casual_male",
        sample_path=p,
        voice_id="v1",
    )
    assert vid == "v1"
