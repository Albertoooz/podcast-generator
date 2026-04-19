"""Word-budget helpers for transcript segments."""

from app.graph.nodes.transcript import (
    _max_dialogue_lines_for_words,
    _trim_dialogue_to_word_budget,
)
from app.models.schema import Dialogue


def test_max_dialogue_lines_for_words_scales_with_budget() -> None:
    assert _max_dialogue_lines_for_words(650) == 32  # int(round(650/20)) with banker's rounding
    assert _max_dialogue_lines_for_words(100) >= 4


def test_trim_dialogue_no_budget_returns_unchanged() -> None:
    lines = [
        Dialogue(speaker="A", dialogue="one two three"),
        Dialogue(speaker="B", dialogue="four five"),
    ]
    assert _trim_dialogue_to_word_budget(lines, None) == lines
    assert _trim_dialogue_to_word_budget(lines, 0) == lines


def test_trim_dialogue_drops_extra_lines() -> None:
    lines = [
        Dialogue(speaker="A", dialogue="w " * 50),  # 50 words
        Dialogue(speaker="B", dialogue="x " * 50),
        Dialogue(speaker="A", dialogue="y " * 50),
    ]
    out = _trim_dialogue_to_word_budget(lines, 80)
    assert sum(len(d.dialogue.split()) for d in out) <= int(80 * 1.12)
    assert len(out) < len(lines)


def test_trim_dialogue_truncates_long_single_line() -> None:
    long_line = "word " * 200
    out = _trim_dialogue_to_word_budget([Dialogue(speaker="A", dialogue=long_line)], 40)
    assert len(out) == 1
    assert len(out[0].dialogue.split()) <= int(40 * 1.12)
