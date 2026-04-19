"""Voice library entries (registered TTS voices / samples)."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field, model_validator


class VoiceEntry(BaseModel):
    """Metadata for a voice usable by speakers (local registry, no API clone call)."""

    label: str = Field(..., description="Human-friendly label")
    provider: str = Field(
        ...,
        description="TTS provider id (elevenlabs, openai, voxtral_cloud, ...)",
    )
    provider_voice_id: str | None = Field(
        default=None,
        description="Provider voice id (ElevenLabs id, OpenAI preset name, Mistral preset)",
    )
    sample_path: str | None = Field(
        default=None,
        description="Local reference audio path (WAV/MP3) for cloning-capable providers",
    )
    style_description: str = ""
    language: str | None = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat(),
    )

    @model_validator(mode="after")
    def check_provider_requirements(self) -> VoiceEntry:
        p = self.provider.lower().strip()
        if p in ("elevenlabs", "openai"):
            if not (self.provider_voice_id and str(self.provider_voice_id).strip()):
                raise ValueError(
                    f"provider '{p}' requires non-empty provider_voice_id "
                    "(ElevenLabs voice id or OpenAI preset: alloy, nova, ...)",
                )
        if p in ("voxtral_cloud", "voxtral_local", "voxtral_mlx", "xtts"):
            has_id = self.provider_voice_id and str(self.provider_voice_id).strip()
            has_sample = self.sample_path and str(self.sample_path).strip()
            if not has_id and not has_sample:
                raise ValueError(
                    f"provider '{p}' needs provider_voice_id (preset) and/or sample_path",
                )
        return self


class VoiceLibrary(BaseModel):
    voices: dict[str, VoiceEntry]
