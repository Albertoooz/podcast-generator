from __future__ import annotations

from pathlib import Path

import pytest

import app.graph.workflow as workflow_mod
from app.graph.workflow import build_graph, create_podcast
from app.models.schema import Dialogue, Outline, Segment
from app.models.speaker import Speaker, SpeakerProfile


@pytest.mark.asyncio
async def test_build_graph_smoke():
    g = build_graph()
    assert g is not None


@pytest.mark.asyncio
async def test_create_podcast_mocked_graph(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)

    class FakeGraph:
        async def ainvoke(self, state, config=None):
            return {
                "outline": Outline(segments=[Segment(name="Intro", description="i", size="short")]),
                "transcript": [Dialogue(speaker="Professor Feynman", dialogue="Hello.")],
                "audio_clips": [],
                "final_output_file_path": None,
            }

    monkeypatch.setattr(workflow_mod, "graph", FakeGraph())
    fake_profile = SpeakerProfile(
        tts_provider="openai",
        tts_model="tts-1",
        speakers=[
            Speaker(name="X", voice_id="alloy", backstory="b", personality="p"),
        ],
    )
    monkeypatch.setattr(
        workflow_mod,
        "resolve_episode_to_speaker_profile",
        lambda *a, **k: fake_profile,
    )

    r = await create_podcast(
        content="x",
        briefing="b",
        episode_name="t",
        output_dir=str(tmp_path / "out"),
        episode_profile="diverse_panel",
    )
    assert r["audio_clips_count"] == 0
    assert (tmp_path / "out" / "outline.json").exists()
