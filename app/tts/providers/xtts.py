"""Optional Coqui XTTS v2 for local multilingual / PL fallback."""

from __future__ import annotations

import asyncio
from pathlib import Path

from loguru import logger

from app.models.speaker import Speaker


class XTTSProvider:
    name = "xtts"

    async def synthesize(self, text: str, speaker: Speaker, output_file: Path) -> Path:
        try:
            from TTS.api import TTS  # type: ignore[import-not-found]
        except ImportError as e:
            raise ImportError(
                "Install optional extra: uv sync --extra xtts (requires Coqui TTS)",
            ) from e

        model_name = speaker.tts_model or "tts_models/multilingual/multi-dataset/xtts_v2"
        sample = speaker.voice_sample_path or speaker.voice_id

        def _run() -> None:
            tts = TTS(model_name)
            lang = "en"
            if speaker.tts_config and "language" in speaker.tts_config:
                lang = str(speaker.tts_config["language"])
            kwargs: dict = {"text": text, "file_path": str(output_file), "language": lang}
            if Path(sample).is_file():
                kwargs["speaker_wav"] = sample
            tts.tts_to_file(**kwargs)

        await asyncio.to_thread(_run)
        logger.debug("XTTS wrote {}", output_file)
        return output_file
