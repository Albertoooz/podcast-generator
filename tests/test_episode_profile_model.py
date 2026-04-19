from __future__ import annotations

from app.models.episode import EpisodeProfile


def test_episode_extra_fields_ignored():
    ep = EpisodeProfile.model_validate(
        {
            "speaker_config": "should_be_ignored",
            "default_briefing": "hi",
            "speakers": ["a"],
        },
    )
    assert ep.default_briefing == "hi"
    assert ep.speakers == ["a"]


def test_episode_only_speakers_list():
    ep = EpisodeProfile(
        default_briefing="hi",
        speakers=["a", "b"],
    )
    assert ep.speakers == ["a", "b"]


def test_episode_without_speakers():
    """JSON with no speakers is valid; generation requires assigning speakers in the UI or file."""
    ep = EpisodeProfile(
        default_briefing="hi",
        speakers=None,
    )
    assert ep.speakers is None
