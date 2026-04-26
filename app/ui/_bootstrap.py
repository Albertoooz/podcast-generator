"""Add repo root to sys.path so ``import app`` works in Streamlit page scripts."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv


def ensure_project_root() -> None:
    d = Path(__file__).resolve().parent
    for _ in range(20):
        if (d / "pyproject.toml").is_file():
            s = str(d)
            if s not in sys.path:
                sys.path.insert(0, s)
            envp = d / ".env"
            if envp.is_file():
                load_dotenv(envp, override=True)
            return
        if d.parent == d:
            break
        d = d.parent


ensure_project_root()
