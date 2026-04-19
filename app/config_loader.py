"""Load episode and speakers library configs with cascade.

Priority: runtime overrides → ``configs/*.json`` → optional ``app/resources/episodes.json``
→ embedded episode default (``diverse_panel`` skeleton; speakers/voices only in ``configs/``).
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any, cast

from loguru import logger

from app.models.episode import EpisodeConfig, EpisodeProfile
from app.models.speaker import SpeakersLibrary

# Module-level overrides (e.g. tests)
_episodes_override: EpisodeConfig | dict[str, Any] | None = None
_episodes_path_override: Path | None = None

# Fallback when no episode file exists yet (``podcast-generator init`` writes ``configs/``).
_EMBEDDED_EPISODES: dict[str, Any] = {
    "profiles": {
        "diverse_panel": {
            "speakers": None,
            "outline_provider": "openai",
            "outline_model": "gpt-4o-mini",
            "transcript_provider": "anthropic",
            "transcript_model": "claude-3-5-sonnet-latest",
            "default_briefing": (
                "Create a dynamic multi-perspective discussion with debate and diverse viewpoints."
            ),
            "num_segments": 5,
        },
    },
}


def default_episodes_dict() -> dict[str, Any]:
    """Deep copy of built-in episode profiles (for ``init`` and tests)."""
    return copy.deepcopy(_EMBEDDED_EPISODES)


def configure(
    key: str,
    value: Any,
) -> None:
    """Set inline configuration (mirrors podcast-creator style)."""
    global _episodes_override, _episodes_path_override
    if key == "episode_config" and isinstance(value, dict):
        _episodes_override = value
    elif key == "episode_config_path":
        _episodes_path_override = Path(value) if value else None
    else:
        logger.warning("Unknown configure key: {}", key)


def _project_root() -> Path:
    return Path.cwd()


def _default_episodes_path() -> Path:
    if _episodes_path_override:
        return _episodes_path_override
    return _project_root() / "configs" / "episodes.json"


def _default_speakers_library_path() -> Path:
    return _project_root() / "configs" / "speakers_library.json"


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


def load_speakers_library() -> SpeakersLibrary:
    """Global speakers library from ``configs/speakers_library.json`` (empty if missing)."""
    path = _default_speakers_library_path()
    if not path.exists():
        return SpeakersLibrary(speakers={})
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return SpeakersLibrary.model_validate(data)


def save_speakers_library(lib: SpeakersLibrary) -> None:
    """Write speakers library atomically to ``configs/speakers_library.json``."""
    _atomic_write_json(_default_speakers_library_path(), lib.model_dump())


def list_library_speaker_ids() -> list[str]:
    return sorted(load_speakers_library().speakers.keys())


def _bundled_episodes_path() -> Path:
    return Path(__file__).resolve().parent / "resources" / "episodes.json"


def load_episode_config_file_dict() -> dict[str, Any]:
    """Episodes JSON from project file or bundled file (ignores programmatic overrides)."""
    path = _default_episodes_path()
    if path.exists():
        with path.open(encoding="utf-8") as f:
            return cast(dict[str, Any], json.load(f))
    bundled = _bundled_episodes_path()
    if bundled.exists():
        with bundled.open(encoding="utf-8") as f:
            return cast(dict[str, Any], json.load(f))
    return default_episodes_dict()


def _load_episode_config_dict() -> dict[str, Any]:
    if _episodes_override is not None:
        if isinstance(_episodes_override, EpisodeConfig):
            return _episodes_override.model_dump()
        return dict(_episodes_override)
    path = _default_episodes_path()
    if path.exists():
        with path.open(encoding="utf-8") as f:
            return cast(dict[str, Any], json.load(f))
    bundled = _bundled_episodes_path()
    if bundled.exists():
        with bundled.open(encoding="utf-8") as f:
            return cast(dict[str, Any], json.load(f))
    return default_episodes_dict()


def load_episode_profile(profile_name: str) -> EpisodeProfile:
    data = _load_episode_config_dict()
    cfg = EpisodeConfig(**data)
    return cfg.get_profile(profile_name)


def list_episode_profile_names() -> list[str]:
    return sorted(_load_episode_config_dict().get("profiles", {}).keys())


def reset_overrides() -> None:
    """Clear programmatic overrides (for tests)."""
    global _episodes_override, _episodes_path_override
    _episodes_override = None
    _episodes_path_override = None
