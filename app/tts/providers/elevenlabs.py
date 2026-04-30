from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from app.models.speaker import Speaker
from app.settings import get_settings, refresh_settings_env

_ELEVEN_API_KEYS_URL = "https://elevenlabs.io/app/settings/api-keys"


def format_elevenlabs_user_error(exc: BaseException) -> str:
    """Readable UI text for ElevenLabs ``ApiError`` (e.g. restricted keys, 401)."""
    try:
        from elevenlabs.core.api_error import ApiError
    except ImportError:
        return str(exc)

    if not isinstance(exc, ApiError):
        return str(exc)

    detail_msg: str | None = None
    body = exc.body
    if isinstance(body, dict):
        d = body.get("detail")
        if isinstance(d, dict):
            detail_msg = d.get("message") if isinstance(d.get("message"), str) else None
        elif isinstance(d, str):
            detail_msg = d
    if exc.status_code == 401 and detail_msg and "voices_read" in detail_msg:
        return (
            "ElevenLabs (401): this API key cannot list voices — it lacks the voices_read "
            "permission (restricted keys). In ElevenLabs → Settings → API keys, create a key with "
            "Voices: Read (and Voices: Write for cloning), "
            f"or use a non-restricted key. {_ELEVEN_API_KEYS_URL}"
        )
    if exc.status_code == 401 and detail_msg and "voices_write" in detail_msg.lower():
        return (
            "ElevenLabs (401): this API key cannot create or edit voices — enable Voices: Write "
            f"on the key, or use a non-restricted key. {_ELEVEN_API_KEYS_URL}"
        )
    if detail_msg:
        return f"ElevenLabs API ({exc.status_code}): {detail_msg}"
    return str(exc)


_ELEVENLABS_PVID_PLACEHOLDERS = frozenset(
    {
        "elevenlabs",
        "eleven",
        "pending",
        "todo",
        "tbd",
        "none",
        "n/a",
        "na",
        "placeholder",
        "your_voice_id",
        "voice_id",
        "id",
    },
)


def elevenlabs_voice_id_looks_assigned(provider_voice_id: str | None) -> bool:
    """True if *provider_voice_id* is non-empty and not an obvious UI placeholder."""
    t = (provider_voice_id or "").strip()
    if not t:
        return False
    return t.lower() not in _ELEVENLABS_PVID_PLACEHOLDERS


def _voice_row_from_sdk(v: Any) -> dict[str, Any]:
    """Normalize SDK ``Voice`` to the same shape as Mistral rows for the UI."""
    cat: str | None = None
    if getattr(v, "category", None) is not None:
        cat = getattr(v.category, "value", None) or str(v.category)
    return {
        "id": v.voice_id,
        "name": (v.name or "").strip() or v.voice_id,
        "category": cat or "",
    }


async def list_voices_on_elevenlabs(
    *,
    api_key: str | None = None,
    show_legacy: bool = True,
) -> list[dict[str, Any]]:
    """List voices on the ElevenLabs account (premade + your clones)."""
    from elevenlabs import AsyncElevenLabs

    refresh_settings_env()
    settings = get_settings()
    key = api_key or settings.elevenlabs_api_key
    if not key:
        raise ValueError("ELEVENLABS_API_KEY is not set")
    client = AsyncElevenLabs(api_key=key)
    resp = await client.voices.get_all(show_legacy=show_legacy)
    rows = [_voice_row_from_sdk(v) for v in resp.voices]
    logger.info("Listed {} ElevenLabs voices", len(rows))
    return rows


async def register_voice_with_elevenlabs(
    name: str,
    sample_path: str | Path,
    *,
    description: str | None = None,
    api_key: str | None = None,
) -> str:
    """Instant voice clone (IVC): upload *sample_path*, return ``voice_id`` for TTS."""
    from elevenlabs import AsyncElevenLabs

    refresh_settings_env()
    settings = get_settings()
    key = api_key or settings.elevenlabs_api_key
    if not key:
        raise ValueError("ELEVENLABS_API_KEY is not set")
    p = Path(sample_path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"Sample not found: {p}")
    suffix = p.suffix.lower()
    if suffix not in (".wav", ".mp3"):
        raise ValueError("ElevenLabs IVC expects a .wav or .mp3 sample path")
    data = p.read_bytes()
    mime = "audio/mpeg" if suffix == ".mp3" else "audio/wav"
    file_entry: tuple[str, bytes, str] = (p.name, data, mime)

    client = AsyncElevenLabs(api_key=key)
    kwargs: dict[str, Any] = {"name": name, "files": [file_entry]}
    if description and description.strip():
        kwargs["description"] = description.strip()
    result = await client.voices.ivc.create(**kwargs)
    vid = str(result.voice_id)
    logger.info("Registered ElevenLabs IVC voice '{}' → {}", name, vid)
    return vid


async def delete_voice_on_elevenlabs(
    voice_id: str,
    *,
    api_key: str | None = None,
) -> None:
    """Delete a voice from the ElevenLabs account (fails for built‑in premade voices)."""
    from elevenlabs import AsyncElevenLabs

    refresh_settings_env()
    settings = get_settings()
    key = api_key or settings.elevenlabs_api_key
    if not key:
        raise ValueError("ELEVENLABS_API_KEY is not set")
    client = AsyncElevenLabs(api_key=key)
    await client.voices.delete(voice_id=voice_id)
    logger.info("Deleted ElevenLabs voice {}", voice_id)


class ElevenLabsProvider:
    name = "elevenlabs"

    async def synthesize(self, text: str, speaker: Speaker, output_file: Path) -> Path:
        settings = get_settings()
        api_key = settings.elevenlabs_api_key
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY is not set")

        model_id = speaker.tts_model or "eleven_flash_v2_5"
        voice_id = speaker.voice_id
        cfg = dict(speaker.tts_config or {})
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        payload: dict = {"text": text, "model_id": model_id, **cfg}
        headers = {"xi-api-key": api_key, "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.content

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(data)
        logger.debug("ElevenLabs TTS wrote {}", output_file)
        return output_file
