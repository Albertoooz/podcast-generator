from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Segment(BaseModel):
    name: str = Field(..., description="Name of the segment")
    description: str = Field(..., description="Description of the segment")
    size: Literal["short", "medium", "long"] = Field(
        default="medium", description="Relative length of the segment"
    )


class Outline(BaseModel):
    segments: list[Segment] = Field(..., description="Ordered podcast segments")

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        return {"segments": [s.model_dump(**kwargs) for s in self.segments]}


class Dialogue(BaseModel):
    speaker: str = Field(..., description="Speaker name")
    dialogue: str = Field(..., description="Spoken line")

    @field_validator("speaker")
    @classmethod
    def strip_speaker(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Speaker name cannot be empty")
        return v.strip()


class Transcript(BaseModel):
    transcript: list[Dialogue] = Field(..., description="Dialogue lines")

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        return {"transcript": [d.model_dump(**kwargs) for d in self.transcript]}
