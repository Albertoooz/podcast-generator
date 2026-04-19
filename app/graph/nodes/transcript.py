import json
import re
from typing import Any, cast

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from loguru import logger

from app.graph.state import PodcastState
from app.llm.factory import get_chat_model
from app.models.schema import Dialogue, Transcript
from app.prompting import render_transcript_prompt
from app.retry import create_retry_decorator, get_retry_config

_WORDS_PER_TURN = 40  # rough average words per dialogue exchange

# LLMs sometimes emit role labels instead of persona names; map to a real speaker by turn index.
_ROLE_LABELS = frozenset(
    {
        "producer",
        "host",
        "co-host",
        "cohost",
        "moderator",
        "narrator",
        "announcer",
        "presenter",
        "interviewer",
        "expert",
        "guest",
        "anchor",
        "speaker",
        "voice",
    },
)


def _normalize_dialogue_speaker(raw: str, allowed: list[str], line_index: int) -> str:
    """Map model output to a canonical speaker name from the profile."""
    t = raw.strip()
    if not t:
        raise ValueError("Empty speaker name in transcript line")
    if t in allowed:
        return t
    by_lower = {a.lower(): a for a in allowed}
    if t.lower() in by_lower:
        return by_lower[t.lower()]
    for name in sorted(allowed, key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", t, re.IGNORECASE):
            return name
    token = re.sub(r"[^\w\s-]", "", t, flags=re.UNICODE).strip().lower()
    if not token:
        token = t.lower()
    first_word = token.split()[0] if token else ""
    if first_word in _ROLE_LABELS or token in _ROLE_LABELS:
        return allowed[line_index % len(allowed)]
    raise ValueError(
        f"Invalid speaker '{raw}'. Expected one of: {allowed}. "
        "Use each speaker's display name exactly as listed under <speakers>.",
    )


def _turns_for_segment(size: str) -> int:
    if size == "short":
        return 3
    if size == "long":
        return 10
    return 6


def _turns_from_words(words: int) -> int:
    """Convert a word-count target to a minimum-turns hint."""
    return max(3, round(words / _WORDS_PER_TURN))


def _word_count(text: str) -> int:
    return len(text.split())


def _max_dialogue_lines_for_words(words: int) -> int:
    """Upper bound on JSON lines so the model (and trimmer) stay near the word budget."""
    # Assume ~18–22 spoken words per short line; cap array size for structured output.
    return max(4, min(120, int(round(words / 20))))


def _truncate_text_to_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def _min_completion_tokens_for_transcript(words_per_segment: int | None) -> int:
    """Lower bound for completion tokens so structured JSON is rarely truncated mid-stream."""
    if not words_per_segment:
        return 8192
    # Spoken text + JSON keys/escapes; Polish etc. can run higher than English token/word.
    return min(32768, max(8192, words_per_segment * 8 + 3072))


def _ensure_transcript_llm_config(
    provider: str, cfg: dict[str, Any], words_per_segment: int | None
) -> dict[str, Any]:
    """Raise provider completion limits when they are unset or too low for a Transcript JSON."""
    out = dict(cfg)
    p = provider.lower().strip()
    floor = _min_completion_tokens_for_transcript(words_per_segment)

    def _bump(key: str) -> None:
        cur = out.get(key)
        if cur is None:
            out[key] = floor
            return
        try:
            iv = int(cur)
        except (TypeError, ValueError):
            return
        if iv > 0 and iv < floor:
            out[key] = floor

    if p == "ollama":
        cur = out.get("num_predict")
        if cur == -1:
            return out
        if cur is None:
            out["num_predict"] = floor
            return out
        try:
            iv = int(cur)
        except (TypeError, ValueError):
            out["num_predict"] = floor
            return out
        if iv > 0 and iv < floor:
            out["num_predict"] = floor
        return out

    if p in (
        "openai",
        "openrouter",
        "open_router",
        "mistral",
        "mistralai",
        "anthropic",
    ):
        has_mct = out.get("max_completion_tokens") is not None
        has_mt = out.get("max_tokens") is not None
        if has_mct:
            _bump("max_completion_tokens")
        if has_mt:
            _bump("max_tokens")
        if not has_mct and not has_mt:
            out["max_tokens"] = floor
        return out

    return out


def _max_words_per_dialogue_line(words: int, max_lines: int) -> int:
    return max(12, min(120, int(words / max(max_lines, 1))))


def _trim_dialogue_to_word_budget(lines: list[Dialogue], budget: int | None) -> list[Dialogue]:
    """Drop / truncate lines so this segment stays near ``budget`` spoken words."""
    if budget is None or budget <= 0 or not lines:
        return lines
    cap = int(budget * 1.12)
    out: list[Dialogue] = []
    total = 0
    for line in lines:
        w = _word_count(line.dialogue)
        remaining = cap - total
        if remaining <= 0:
            break
        if w <= remaining:
            out.append(line)
            total += w
            continue
        truncated = _truncate_text_to_words(line.dialogue, remaining).strip()
        if truncated:
            out.append(Dialogue(speaker=line.speaker, dialogue=truncated))
        break
    if not out and lines:
        first = lines[0]
        t = _truncate_text_to_words(first.dialogue, min(cap, max(1, budget))).strip()
        return [Dialogue(speaker=first.speaker, dialogue=t or first.dialogue[:200])]
    return out


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
    transcript_cfg = _ensure_transcript_llm_config(
        provider,
        dict(configurable.get("transcript_config") or {}),
        state.get("words_per_segment"),
    )

    llm = get_chat_model(provider, model_name, **transcript_cfg).with_structured_output(Transcript)
    retry_cfg = get_retry_config(configurable)
    llm_retry = create_retry_decorator(**retry_cfg)

    @llm_retry
    async def _invoke(prompt: str) -> Transcript:
        msg = HumanMessage(content=prompt)
        return cast(Transcript, await llm.ainvoke([msg], config=config))

    transcript: list[Dialogue] = []
    outline_json = json.dumps(outline.model_dump(), indent=2)

    words_per_segment: int | None = state.get("words_per_segment")

    for i, segment in enumerate(outline.segments):
        is_final = i == len(outline.segments) - 1
        if words_per_segment:
            turns = _turns_from_words(words_per_segment)
            max_dialogue_lines = _max_dialogue_lines_for_words(words_per_segment)
            max_words_per_line = _max_words_per_dialogue_line(
                words_per_segment,
                max_dialogue_lines,
            )
        else:
            turns = _turns_for_segment(segment.size)
            max_dialogue_lines = None
            max_words_per_line = None
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
                "max_dialogue_lines": max_dialogue_lines,
                "max_words_per_line": max_words_per_line,
                "speaker_names": speaker_names,
                "format_instructions": "",
            }
        )

        batch = await _invoke(prompt)
        trimmed = _trim_dialogue_to_word_budget(batch.transcript, words_per_segment)
        if words_per_segment and len(trimmed) < len(batch.transcript):
            logger.warning(
                "Trimmed transcript segment {} from {} to {} lines to respect ~{} words",
                i,
                len(batch.transcript),
                len(trimmed),
                words_per_segment,
            )
        for j, line in enumerate(trimmed):
            idx = len(transcript) + j
            canonical = _normalize_dialogue_speaker(line.speaker, speaker_names, idx)
            if canonical != line.speaker:
                logger.warning(
                    "Remapped transcript speaker '{}' → '{}' (segment {})",
                    line.speaker,
                    canonical,
                    i,
                )
                line = Dialogue(speaker=canonical, dialogue=line.dialogue)
            transcript.append(line)

    logger.info("Transcript has {} lines", len(transcript))
    return {"transcript": transcript}
