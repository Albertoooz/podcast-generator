import asyncio
from pathlib import Path

from loguru import logger

from app.models.speaker import Speaker
from app.settings import get_settings


class OpenAITTSProvider:
    name = "openai"

    async def synthesize(self, text: str, speaker: Speaker, output_file: Path) -> Path:
        from openai import OpenAI

        settings = get_settings()
        client = OpenAI(api_key=settings.openai_api_key)
        model = speaker.tts_model or "gpt-4o-mini-tts"
        voice = speaker.voice_id
        cfg = dict(speaker.tts_config or {})

        def _sync() -> None:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            resp = client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                **cfg,
            )
            if hasattr(resp, "stream_to_file"):
                resp.stream_to_file(str(output_file))
            else:
                output_file.write_bytes(getattr(resp, "content", b"") or b"")

        await asyncio.to_thread(_sync)
        logger.debug("OpenAI TTS wrote {}", output_file)
        return output_file
