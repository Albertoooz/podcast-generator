import json
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from loguru import logger

from app.graph.state import PodcastState
from app.llm.factory import get_chat_model
from app.models.schema import Dialogue, Transcript
from app.prompting import render_transcript_prompt
from app.retry import create_retry_decorator, get_retry_config

_WORDS_PER_TURN = 40  # rough average words per dialogue exchange


def _turns_for_segment(size: str) -> int:
    if size == "short":
        return 3
    if size == "long":
        return 10
    return 6


def _turns_from_words(words: int) -> int:
    """Convert a word-count target to a minimum-turns hint."""
    return max(3, round(words / _WORDS_PER_TURN))


async def generate_transcript_node(state: PodcastState, config: RunnableConfig) -> dict[str, Any]:
    logger.info("Starting transcript generation")
    outline = state.get("outline")
    assert outline is not None
    sp = state["speaker_profile"]
    assert sp is not None
    speaker_names = sp.get_speaker_names()

    configurable = config.get("configurable") or {}
    provider = configurable.get("transcript_provider", "openai")
    model_name = configurable.get("transcript_model", "gpt-4o-mini")
    transcript_cfg = dict(configurable.get("transcript_config") or {})

    llm = get_chat_model(provider, model_name, **transcript_cfg).with_structured_output(Transcript)
    retry_cfg = get_retry_config(configurable)
    llm_retry = create_retry_decorator(**retry_cfg)

    @llm_retry
    async def _invoke(prompt: str) -> Transcript:
        msg = HumanMessage(content=prompt)
        return await llm.ainvoke([msg], config=config)

    transcript: list[Dialogue] = []
    outline_json = json.dumps(outline.model_dump(), indent=2)

    words_per_segment: int | None = state.get("words_per_segment")

    for i, segment in enumerate(outline.segments):
        is_final = i == len(outline.segments) - 1
        if words_per_segment:
            turns = _turns_from_words(words_per_segment)
        else:
            turns = _turns_for_segment(segment.size)
        prior = json.dumps([d.model_dump() for d in transcript], indent=2) if transcript else ""
        segment_json = json.dumps(segment.model_dump(), indent=2)

        prompt = render_transcript_prompt(
            {
                "briefing": state["briefing"],
                "context": state["content"],
                "speakers": sp.speakers,
                "language": state.get("language"),
                "outline_json": outline_json,
                "segment_json": segment_json,
                "prior_transcript": prior,
                "transcript": transcript,
                "segment": segment,
                "is_final": is_final,
                "turns": turns,
                "words_per_segment": words_per_segment,
                "speaker_names": speaker_names,
                "format_instructions": "",
            }
        )

        batch = await _invoke(prompt)
        for line in batch.transcript:
            if line.speaker not in speaker_names:
                raise ValueError(
                    f"Invalid speaker '{line.speaker}'. Expected one of: {speaker_names}",
                )
            transcript.append(line)

    logger.info("Transcript has {} lines", len(transcript))
    return {"transcript": transcript}
