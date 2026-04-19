"""Load Jinja2 templates from ./prompts or bundled resources."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models.speaker import Speaker


def _prompts_dir() -> Path:
    cwd = Path.cwd() / "prompts"
    if cwd.is_dir():
        return cwd
    return Path(__file__).resolve().parent / "resources" / "prompts"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_prompts_dir())),
        autoescape=select_autoescape(enabled_extensions=()),
    )


def render_outline_prompt(data: dict[str, Any]) -> str:
    data = {**data, "format_instructions": data.get("format_instructions", "")}
    return _env().get_template("outline.jinja").render(**data)


def render_transcript_prompt(data: dict[str, Any]) -> str:
    data = {**data, "format_instructions": data.get("format_instructions", "")}
    return _env().get_template("transcript.jinja").render(**data)


def speakers_for_prompt(speakers: list[Speaker]) -> list[Speaker]:
    return speakers
