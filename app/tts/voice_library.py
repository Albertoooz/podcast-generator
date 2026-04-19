"""Voice library persisted in ``configs/voices.json`` (legacy metadata merged on read)."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger

from app.models.voice import VoiceEntry, VoiceLibrary

_UNSET = object()


def voices_dir() -> Path:
    return Path.cwd() / "voices"


def metadata_path() -> Path:
    """Legacy flat metadata (pre–voices.json)."""
    return voices_dir() / "metadata.json"


def _project_voices_json() -> Path:
    return Path.cwd() / "configs" / "voices.json"


def _bundled_voices_json() -> Path:
    return Path(__file__).resolve().parent.parent / "resources" / "voices.json"


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def _migrate_legacy_metadata() -> dict[str, Any]:
    """Convert legacy ``voices/metadata.json`` into ``{voices: {...}}`` shape."""
    legacy_path = metadata_path()
    if not legacy_path.exists():
        return {"voices": {}}
    try:
        with legacy_path.open(encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"voices": {}}
    voices: dict[str, Any] = {}
    for vid, meta in old.items():
        if not isinstance(meta, dict):
            continue
        sample = meta.get("sample_path")
        voices[vid] = {
            "label": vid,
            "provider": "voxtral_cloud",
            "provider_voice_id": "casual_male",
            "sample_path": sample,
            "style_description": meta.get("style_description", ""),
            "language": meta.get("language"),
            "created_at": meta.get("created_at", datetime.now(UTC).isoformat()),
        }
    return {"voices": voices}


def _load_raw() -> dict[str, Any]:
    proj = _project_voices_json()
    if proj.exists():
        with proj.open(encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "voices" in data:
            return data
        # old mistake: flat dict
        if isinstance(data, dict) and data and "voices" not in data:
            return {"voices": dict(data)}
    merged_voices: dict[str, Any] = {}
    bundled = _bundled_voices_json()
    if bundled.exists():
        with bundled.open(encoding="utf-8") as f:
            base = json.load(f)
        if isinstance(base, dict) and "voices" in base:
            merged_voices.update(base["voices"])
    leg = _migrate_legacy_metadata().get("voices") or {}
    merged_voices.update(leg)
    return {"voices": merged_voices}


def load_voice_library() -> VoiceLibrary:
    raw = _load_raw()
    return VoiceLibrary.model_validate(raw)


def _save_library(lib: VoiceLibrary) -> None:
    _atomic_write_json(_project_voices_json(), lib.model_dump())


def list_voices() -> list[str]:
    return sorted(load_voice_library().voices.keys())


def get_voice(voice_id: str) -> dict[str, Any] | None:
    lib = load_voice_library()
    v = lib.voices.get(voice_id)
    if v is None:
        return None
    return v.model_dump()


def add_voice(
    label: str,
    provider: str,
    *,
    provider_voice_id: str | None = None,
    sample_path: Path | str | None = None,
    style_description: str = "",
    language: str | None = None,
    voice_id: str | None = None,
) -> str:
    """Register a voice. Returns library key."""
    vid = voice_id or f"voice_{uuid.uuid4().hex[:8]}"
    lib = load_voice_library()
    sp = str(sample_path) if sample_path else None
    entry = VoiceEntry(
        label=label,
        provider=provider,
        provider_voice_id=provider_voice_id,
        sample_path=sp,
        style_description=style_description,
        language=language,
    )
    voices = dict(lib.voices)
    voices[vid] = entry
    _save_library(VoiceLibrary(voices=voices))
    logger.info("Registered voice {} ({})", vid, provider)
    return vid


def remove_voice(voice_id: str) -> bool:
    lib = load_voice_library()
    if voice_id not in lib.voices:
        return False
    voices = dict(lib.voices)
    del voices[voice_id]
    _save_library(VoiceLibrary(voices=voices))
    return True


def update_voice(
    voice_id: str,
    *,
    label: Any = _UNSET,
    provider: Any = _UNSET,
    provider_voice_id: Any = _UNSET,
    sample_path: Any = _UNSET,
    style_description: Any = _UNSET,
    language: Any = _UNSET,
) -> bool:
    """Update fields; omit using _UNSET to leave unchanged."""
    lib = load_voice_library()
    if voice_id not in lib.voices:
        return False
    cur = lib.voices[voice_id].model_dump()
    if label is not _UNSET:
        cur["label"] = label
    if provider is not _UNSET:
        cur["provider"] = provider
    if provider_voice_id is not _UNSET:
        cur["provider_voice_id"] = provider_voice_id
    if sample_path is not _UNSET:
        cur["sample_path"] = str(sample_path) if sample_path else None
    if style_description is not _UNSET:
        cur["style_description"] = style_description
    if language is not _UNSET:
        cur["language"] = (
            language.strip() if isinstance(language, str) and language.strip() else None
        )
    entry = VoiceEntry.model_validate(cur)
    voices = dict(lib.voices)
    voices[voice_id] = entry
    _save_library(VoiceLibrary(voices=voices))
    logger.info("Updated voice {}", voice_id)
    return True
