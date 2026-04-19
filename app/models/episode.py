from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EpisodeProfile(BaseModel):
    """Episode template: ``speakers`` = 1–4 ids from the speakers library (required to run)."""

    model_config = ConfigDict(extra="ignore")

    speakers: list[str] | None = Field(
        default=None,
        description="Speaker ids from configs/speakers_library.json (1–4)",
    )
    outline_provider: str = Field(default="openai")
    outline_model: str = Field(default="gpt-4o-mini")
    outline_temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="LLM temperature for outline generation (0 = deterministic, 2 = max creative).",
    )
    transcript_provider: str = Field(default="anthropic")
    transcript_model: str = Field(default="claude-3-5-sonnet-latest")
    transcript_temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="LLM temperature for transcript generation.",
    )
    default_briefing: str = Field(..., description="Default briefing when none given")
    num_segments: int = Field(
        default=4,
        ge=1,
        le=20,
        description=(
            "Number of segments (chapters) in the episode. "
            "Each segment covers one topic from the outline."
        ),
    )
    words_per_segment: int | None = Field(
        default=None,
        ge=50,
        le=2000,
        description=(
            "Target word count per segment. "
            "Approx 130 words ≈ 1 minute of speech. "
            "If None, the LLM decides based on segment size hints."
        ),
    )
    outline_config: dict[str, Any] | None = Field(
        default=None,
        description="Extra kwargs forwarded to the outline LLM (e.g. top_p, max_tokens).",
    )
    transcript_config: dict[str, Any] | None = Field(
        default=None,
        description="Extra kwargs forwarded to the transcript LLM.",
    )
    language: str | None = None

    @field_validator("speakers")
    @classmethod
    def validate_speakers_len(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        if not v:
            return None
        if len(v) > 4:
            raise ValueError("At most 4 speakers per episode")
        return v


def merge_episode_form(base: EpisodeProfile, overrides: dict[str, Any]) -> EpisodeProfile:
    """Overlay form/UI values onto a saved profile. Keeps base model names if override is empty."""
    data = base.model_dump()
    for key, val in overrides.items():
        if key in ("outline_model", "transcript_model") and val == "":
            continue
        data[key] = val
    return EpisodeProfile.model_validate(data)


class EpisodeConfig(BaseModel):
    profiles: dict[str, EpisodeProfile]

    def get_profile(self, name: str) -> EpisodeProfile:
        if name not in self.profiles:
            raise ValueError(f"Episode profile '{name}' not found")
        return self.profiles[name]

    @classmethod
    def load_from_file(cls, path: str) -> "EpisodeConfig":
        import json
        from pathlib import Path

        p = Path(path)
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
