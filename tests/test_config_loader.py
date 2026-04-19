from __future__ import annotations

from pathlib import Path

import pytest

from app.config_loader import (
    configure,
    list_episode_profile_names,
    load_episode_config_file_dict,
    load_episode_profile,
    reset_overrides,
)


def test_load_episode_profile_from_bundled_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    reset_overrides()
    monkeypatch.chdir(tmp_path)
    ep = load_episode_profile("diverse_panel")
    assert ep.num_segments >= 1
    assert ep.speakers is None


def test_configure_inline_episode_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    reset_overrides()
    monkeypatch.chdir(tmp_path)
    configure(
        "episode_config",
        {
            "profiles": {
                "custom": {
                    "speakers": ["demo_host"],
                    "outline_provider": "openai",
                    "outline_model": "gpt-4o-mini",
                    "transcript_provider": "openai",
                    "transcript_model": "gpt-4o-mini",
                    "default_briefing": "x",
                    "num_segments": 2,
                },
            },
        },
    )
    ep = load_episode_profile("custom")
    assert ep.num_segments == 2
    reset_overrides()


def test_list_episode_profile_names(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    reset_overrides()
    monkeypatch.chdir(tmp_path)
    assert "diverse_panel" in list_episode_profile_names()


def test_load_episode_config_file_dict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    reset_overrides()
    monkeypatch.chdir(tmp_path)
    raw = load_episode_config_file_dict()
    assert "profiles" in raw
    assert "diverse_panel" in raw["profiles"]
