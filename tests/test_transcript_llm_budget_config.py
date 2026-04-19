"""Transcript LLM completion limits (avoid truncated structured JSON)."""

from app.graph.nodes.transcript import (
    _ensure_transcript_llm_config,
    _min_completion_tokens_for_transcript,
)


def test_min_completion_tokens_scales_with_words() -> None:
    assert _min_completion_tokens_for_transcript(None) == 8192
    assert _min_completion_tokens_for_transcript(650) >= 8192
    assert _min_completion_tokens_for_transcript(2000) <= 32768


def test_ensure_openai_bumps_low_max_tokens() -> None:
    cfg = _ensure_transcript_llm_config("openai", {"max_tokens": 512, "temperature": 0.2}, 650)
    assert cfg["max_tokens"] >= 8192
    assert cfg["temperature"] == 0.2


def test_ensure_openai_sets_default_when_missing() -> None:
    cfg = _ensure_transcript_llm_config("openai", {}, None)
    assert cfg.get("max_tokens") == 8192


def test_ensure_ollama_bumps_num_predict() -> None:
    cfg = _ensure_transcript_llm_config("ollama", {"num_predict": 256}, 650)
    assert cfg["num_predict"] >= 8192


def test_ensure_ollama_respects_infinite_num_predict() -> None:
    cfg = _ensure_transcript_llm_config("ollama", {"num_predict": -1}, 650)
    assert cfg["num_predict"] == -1
