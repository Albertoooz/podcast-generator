"""LangGraph workflow and high-level create_podcast API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.config_loader import load_episode_profile, load_speakers_library
from app.graph.nodes import (
    combine_audio_node,
    generate_all_audio_node,
    generate_outline_node,
    generate_transcript_node,
)
from app.graph.state import PodcastState
from app.language import resolve_language_name
from app.models.episode import EpisodeProfile
from app.observability import get_langfuse_callbacks
from app.services.speaker_resolver import resolve_episode_to_speaker_profile
from app.tts.voice_library import load_voice_library


def build_graph():
    workflow = StateGraph(PodcastState)
    workflow.add_node("generate_outline", generate_outline_node)
    workflow.add_node("generate_transcript", generate_transcript_node)
    workflow.add_node("generate_all_audio", generate_all_audio_node)
    workflow.add_node("combine_audio", combine_audio_node)
    workflow.add_edge(START, "generate_outline")
    workflow.add_edge("generate_outline", "generate_transcript")
    workflow.add_edge("generate_transcript", "generate_all_audio")
    workflow.add_edge("generate_all_audio", "combine_audio")
    workflow.add_edge("combine_audio", END)
    return workflow.compile()


graph = build_graph()


async def create_podcast(
    content: str | list[str],
    briefing: str | None = None,
    episode_name: str | None = None,
    output_dir: str | None = None,
    outline_provider: str | None = None,
    outline_model: str | None = None,
    transcript_provider: str | None = None,
    transcript_model: str | None = None,
    num_segments: int | None = None,
    episode_profile: str | None = None,
    episode: EpisodeProfile | None = None,
    briefing_suffix: str | None = None,
    outline_config: dict[str, Any] | None = None,
    transcript_config: dict[str, Any] | None = None,
    retry_max_attempts: int | None = None,
    retry_wait_multiplier: int | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    ep = None
    if episode is not None:
        ep = episode
    elif episode_profile:
        ep = load_episode_profile(episode_profile)

    words_per_segment: int | None = None
    if ep is not None:
        outline_provider = outline_provider or ep.outline_provider
        outline_model = outline_model or ep.outline_model
        transcript_provider = transcript_provider or ep.transcript_provider
        transcript_model = transcript_model or ep.transcript_model
        num_segments = num_segments or ep.num_segments
        words_per_segment = ep.words_per_segment
        outline_config = outline_config if outline_config is not None else ep.outline_config
        transcript_config = (
            transcript_config if transcript_config is not None else ep.transcript_config
        )
        # Fold dedicated temperature fields into the config dicts.
        if ep.outline_temperature is not None:
            outline_config = {**(outline_config or {}), "temperature": ep.outline_temperature}
        if ep.transcript_temperature is not None:
            transcript_config = {
                **(transcript_config or {}),
                "temperature": ep.transcript_temperature,
            }
        language = language or ep.language

        if briefing:
            resolved_briefing = briefing
        elif briefing_suffix:
            resolved_briefing = f"{ep.default_briefing}\n\nAdditional focus: {briefing_suffix}"
        else:
            resolved_briefing = ep.default_briefing
    else:
        outline_provider = outline_provider or "openai"
        outline_model = outline_model or "gpt-4o-mini"
        transcript_provider = transcript_provider or "openai"
        transcript_model = transcript_model or "gpt-4o-mini"
        num_segments = num_segments or 3
        resolved_briefing = briefing or ""

    if not episode_name:
        raise ValueError("episode_name is required")
    if not output_dir:
        raise ValueError("output_dir is required")
    if not resolved_briefing:
        raise ValueError(
            "briefing is required (directly, via episode_profile, or with briefing_suffix)",
        )

    resolved_language = resolve_language_name(language) if language else None
    if ep is None:
        raise ValueError(
            "episode_profile or episode is required (speakers come from the episode + library).",
        )
    speaker_profile = resolve_episode_to_speaker_profile(
        ep,
        speakers_lib=load_speakers_library(),
        voices_lib=load_voice_library(),
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    initial: PodcastState = {
        "content": content,
        "briefing": resolved_briefing,
        "num_segments": num_segments or 3,
        "words_per_segment": words_per_segment,
        "language": resolved_language,
        "outline": None,
        "transcript": [],
        "audio_clips": [],
        "final_output_file_path": None,
        "output_dir": output_path,
        "episode_name": episode_name,
        "speaker_profile": speaker_profile,
    }

    configurable: dict[str, Any] = {
        "outline_provider": outline_provider,
        "outline_model": outline_model,
        "transcript_provider": transcript_provider,
        "transcript_model": transcript_model,
        "outline_config": outline_config or {},
        "transcript_config": transcript_config or {},
    }
    if retry_max_attempts is not None:
        configurable["retry_max_attempts"] = retry_max_attempts
    if retry_wait_multiplier is not None:
        configurable["retry_wait_multiplier"] = retry_wait_multiplier

    callbacks = get_langfuse_callbacks({"episode": episode_name})
    run_config: dict[str, Any] = {
        "configurable": configurable,
        "metadata": {"episode_name": episode_name},
    }
    if callbacks:
        run_config["callbacks"] = callbacks

    result = await graph.ainvoke(initial, config=run_config)

    if result.get("outline"):
        (output_path / "outline.json").write_text(
            result["outline"].model_dump_json(indent=2),
            encoding="utf-8",
        )
    if result.get("transcript"):
        (output_path / "transcript.json").write_text(
            json.dumps([d.model_dump() for d in result["transcript"]], indent=2),
            encoding="utf-8",
        )

    return {
        "outline": result.get("outline"),
        "transcript": result.get("transcript"),
        "final_output_file_path": result.get("final_output_file_path"),
        "audio_clips_count": len(result.get("audio_clips") or []),
        "output_dir": output_path,
    }
