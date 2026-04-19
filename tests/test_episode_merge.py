from __future__ import annotations

from app.models.episode import EpisodeProfile, merge_episode_form


def test_merge_episode_form_keeps_models_when_ui_empty_string():
    base = EpisodeProfile(
        outline_provider="openai",
        outline_model="gpt-4o-mini",
        transcript_provider="openrouter",
        transcript_model="openai/gpt-4o-mini",
        default_briefing="x",
        num_segments=3,
        speakers=["s1"],
    )
    merged = merge_episode_form(
        base,
        {
            "outline_provider": "openrouter",
            "outline_model": "",
            "transcript_model": "",
        },
    )
    assert merged.outline_provider == "openrouter"
    assert merged.outline_model == "gpt-4o-mini"
    assert merged.transcript_model == "openai/gpt-4o-mini"


def test_merge_episode_form_overrides_models_when_set():
    base = EpisodeProfile(
        outline_provider="openai",
        outline_model="gpt-4o-mini",
        transcript_provider="openai",
        transcript_model="gpt-4o-mini",
        default_briefing="x",
        num_segments=3,
        speakers=["s1"],
    )
    merged = merge_episode_form(
        base,
        {"outline_model": "openai/gpt-4o", "transcript_model": "anthropic/claude-3.5-sonnet"},
    )
    assert merged.outline_model == "openai/gpt-4o"
    assert merged.transcript_model == "anthropic/claude-3.5-sonnet"
