"""ElevenLabs voice list / IVC helpers."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tts.providers.elevenlabs import (
    _voice_row_from_sdk,
    elevenlabs_voice_id_looks_assigned,
    format_elevenlabs_user_error,
    list_voices_on_elevenlabs,
    register_voice_with_elevenlabs,
)


def test_elevenlabs_voice_id_looks_assigned() -> None:
    assert not elevenlabs_voice_id_looks_assigned(None)
    assert not elevenlabs_voice_id_looks_assigned("")
    assert not elevenlabs_voice_id_looks_assigned("  elevenlabs  ")
    assert elevenlabs_voice_id_looks_assigned("21m00Tcm4TlvDq8ikWAM")


def test_format_elevenlabs_user_error_voices_read() -> None:
    from elevenlabs.core.api_error import ApiError

    exc = ApiError(
        status_code=401,
        headers={},
        body={
            "detail": {
                "status": "missing_permissions",
                "message": (
                    "The API key you used is missing the permission voices_read "
                    "to execute this operation."
                ),
            }
        },
    )
    msg = format_elevenlabs_user_error(exc)
    assert "voices_read" in msg
    assert "elevenlabs.io" in msg


def test_format_elevenlabs_user_error_generic_api_error() -> None:
    from elevenlabs.core.api_error import ApiError

    exc = ApiError(status_code=403, body={"detail": {"message": "Nope"}})
    assert "Nope" in format_elevenlabs_user_error(exc)


def test_voice_row_from_sdk_enum_category() -> None:
    v = SimpleNamespace(
        voice_id="v1",
        name="Ann",
        category=SimpleNamespace(value="cloned"),
    )
    assert _voice_row_from_sdk(v) == {"id": "v1", "name": "Ann", "category": "cloned"}


def test_voice_row_from_sdk_missing_name() -> None:
    v = SimpleNamespace(voice_id="x9", name=None, category=None)
    assert _voice_row_from_sdk(v) == {"id": "x9", "name": "x9", "category": ""}


@pytest.mark.asyncio
async def test_list_voices_on_elevenlabs_requires_key() -> None:
    with patch("app.tts.providers.elevenlabs.get_settings") as gs:
        gs.return_value = MagicMock(elevenlabs_api_key=None)
        with pytest.raises(ValueError, match="ELEVENLABS_API_KEY"):
            await list_voices_on_elevenlabs()


@pytest.mark.asyncio
async def test_list_voices_on_elevenlabs_returns_rows() -> None:
    v = SimpleNamespace(
        voice_id="abc",
        name="Test",
        category=SimpleNamespace(value="premade"),
    )
    mock_resp = SimpleNamespace(voices=[v])
    mock_client = MagicMock()
    mock_client.voices.get_all = AsyncMock(return_value=mock_resp)
    with patch("app.tts.providers.elevenlabs.get_settings") as gs:
        gs.return_value = MagicMock(elevenlabs_api_key="secret")
    with patch("elevenlabs.AsyncElevenLabs", return_value=mock_client):
        rows = await list_voices_on_elevenlabs()
    assert rows == [{"id": "abc", "name": "Test", "category": "premade"}]
    mock_client.voices.get_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_voice_with_elevenlabs_wrong_suffix(tmp_path) -> None:
    p = tmp_path / "voice.webm"
    p.write_bytes(b"x")
    with pytest.raises(ValueError, match="wav or .mp3"):
        await register_voice_with_elevenlabs("n", p, api_key="k")


@pytest.mark.asyncio
async def test_register_voice_with_elevenlabs_calls_ivc(tmp_path) -> None:
    wav = tmp_path / "s.wav"
    wav.write_bytes(b"fakepcm")
    mock_result = SimpleNamespace(voice_id="new-id")
    mock_client = MagicMock()
    mock_client.voices.ivc.create = AsyncMock(return_value=mock_result)
    with patch("app.tts.providers.elevenlabs.get_settings") as gs:
        gs.return_value = MagicMock(elevenlabs_api_key="secret")
    with patch("elevenlabs.AsyncElevenLabs", return_value=mock_client):
        vid = await register_voice_with_elevenlabs("My clone", wav, description="d")
    assert vid == "new-id"
    mock_client.voices.ivc.create.assert_awaited_once()
    call_kw = mock_client.voices.ivc.create.await_args.kwargs
    assert call_kw["name"] == "My clone"
    assert call_kw["description"] == "d"
    assert len(call_kw["files"]) == 1
    fn, data, mime = call_kw["files"][0]
    assert fn == "s.wav"
    assert data == b"fakepcm"
    assert mime == "audio/wav"
