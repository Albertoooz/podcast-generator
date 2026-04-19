"""Speaker name normalization for transcript lines (LLM role-label quirks)."""

from __future__ import annotations

import pytest

from app.graph.nodes.transcript import _normalize_dialogue_speaker


def test_exact_and_case_insensitive():
    allowed = ["Albert", "Adolf"]
    assert _normalize_dialogue_speaker("Albert", allowed, 0) == "Albert"
    assert _normalize_dialogue_speaker("albert", allowed, 0) == "Albert"


def test_embedded_name_in_string():
    allowed = ["Albert", "Adolf"]
    assert _normalize_dialogue_speaker("Albert (host)", allowed, 0) == "Albert"


def test_role_label_round_robin():
    allowed = ["Albert", "Adolf"]
    assert _normalize_dialogue_speaker("Producer", allowed, 0) == "Albert"
    assert _normalize_dialogue_speaker("Producer", allowed, 1) == "Adolf"
    assert _normalize_dialogue_speaker("Producer", allowed, 2) == "Albert"


def test_unknown_raises():
    with pytest.raises(ValueError, match="Invalid speaker"):
        _normalize_dialogue_speaker("SomeoneElse", ["Albert", "Adolf"], 0)
