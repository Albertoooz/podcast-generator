"""Persist speaker avatar images under ``avatars/`` (project root)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def avatars_dir() -> Path:
    return Path.cwd() / "avatars"


def _safe_slug(slug: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", slug.strip())[:80]
    return s or "avatar"


def save_avatar(file: Any, slug: str) -> Path:
    """Write uploaded image bytes to ``avatars/{slug}_{suffix}.ext``."""
    avatars_dir().mkdir(parents=True, exist_ok=True)
    name = Path(file.name).suffix.lower()
    if name not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        name = ".png"
    safe = _safe_slug(slug)
    out = avatars_dir() / f"{safe}{name}"
    # avoid clobber if same slug different session
    n = 0
    while out.exists():
        n += 1
        out = avatars_dir() / f"{safe}_{n}{name}"
    out.write_bytes(file.getvalue())
    return out.resolve()
