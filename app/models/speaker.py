from typing import Any

from pydantic import BaseModel, Field, field_validator


class Speaker(BaseModel):
    name: str = Field(..., description="Speaker display name")
    voice_id: str = Field(
        ...,
        description="Provider voice id or preset (used when no voice_sample_path)",
    )
    backstory: str = Field(..., description="Background for LLM context")
    personality: str = Field(..., description="Speaking traits for LLM context")
    style_description: str = Field(
        default="",
        description="How this voice should sound in dialogue (prosody, pacing, tone)",
    )
    voice_sample_path: str | None = Field(
        default=None,
        description="Path to reference audio for zero-shot cloning (WAV/MP3)",
    )
    avatar_path: str | None = Field(
        default=None,
        description="Optional path to speaker avatar image (PNG/JPG) used in UI",
    )
    tts_provider: str | None = Field(
        default=None,
        description="Override TTS provider for this speaker",
    )
    tts_model: str | None = Field(
        default=None,
        description="Override TTS model for this speaker",
    )
    tts_config: dict[str, Any] | None = Field(
        default=None,
        description="Extra kwargs for TTS provider",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Speaker name cannot be empty")
        return v.strip()


class SpeakerProfile(BaseModel):
    tts_provider: str = Field(..., description="Default TTS provider id")
    tts_model: str = Field(..., description="Default TTS model name")
    speakers: list[Speaker] = Field(..., min_length=1, max_length=4)
    tts_config: dict[str, Any] | None = Field(
        default=None,
        description="Default kwargs for AIFactory-equivalent TTS construction",
    )

    @field_validator("speakers")
    @classmethod
    def unique_speaker_names(cls, speakers: list[Speaker]) -> list[Speaker]:
        names = [s.name for s in speakers]
        if len(names) != len(set(names)):
            raise ValueError("Speaker names must be unique")
        return speakers

    def get_speaker_names(self) -> list[str]:
        return [s.name for s in self.speakers]

    def get_voice_mapping(self) -> dict[str, str]:
        return {s.name: s.voice_id for s in self.speakers}

    def get_speaker_by_name(self, name: str) -> Speaker:
        for s in self.speakers:
            if s.name == name:
                return s
        raise ValueError(f"Speaker '{name}' not found in profile")


class SpeakerEntry(BaseModel):
    """Global speaker definition (library id → persona + optional voice ref)."""

    name: str = Field(..., description="Display name")
    short_bio: str = Field(default="", description="Short line for UI tiles")
    backstory: str = Field(default="", description="Background for LLM context")
    personality: str = Field(default="", description="Speaking traits for LLM")
    style_description: str = Field(
        default="",
        description="How this voice should sound in dialogue",
    )
    voice_ref: str | None = Field(
        default=None,
        description="Key in VoiceLibrary; None = use tts_* fields below",
    )
    tts_provider: str | None = Field(
        default=None,
        description="If no voice_ref: TTS provider (default openai). Ignored when voice_ref set.",
    )
    tts_model: str | None = Field(
        default=None,
        description="If voice_ref is None: optional TTS model override for that provider.",
    )
    tts_voice_preset: str | None = Field(
        default=None,
        description="If no voice_ref: preset (e.g. alloy, casual_male for Mistral Voxtral).",
    )
    avatar_path: str | None = Field(default=None, description="Optional avatar image path")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Speaker name cannot be empty")
        return v.strip()


class SpeakersLibrary(BaseModel):
    speakers: dict[str, SpeakerEntry]
