from operator import add
from pathlib import Path
from typing import Annotated, TypedDict

from app.models.schema import Dialogue, Outline
from app.models.speaker import SpeakerProfile


class PodcastState(TypedDict):
    content: str | list[str]
    briefing: str
    num_segments: int
    words_per_segment: int | None
    language: str | None

    outline: Outline | None
    transcript: list[Dialogue]

    audio_clips: Annotated[list[Path], add]
    final_output_file_path: Path | None

    output_dir: Path
    episode_name: str
    speaker_profile: SpeakerProfile | None
