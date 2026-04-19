from pathlib import Path
from typing import Protocol, runtime_checkable

from app.models.speaker import Speaker


@runtime_checkable
class TTSProvider(Protocol):
    name: str

    async def synthesize(self, text: str, speaker: Speaker, output_file: Path) -> Path:
        """Write audio to output_file (typically .mp3)."""
        ...
