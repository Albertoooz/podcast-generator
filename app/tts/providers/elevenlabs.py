from pathlib import Path

import httpx
from loguru import logger

from app.models.speaker import Speaker
from app.settings import get_settings


class ElevenLabsProvider:
    name = "elevenlabs"

    async def synthesize(self, text: str, speaker: Speaker, output_file: Path) -> Path:
        settings = get_settings()
        api_key = settings.elevenlabs_api_key
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY is not set")

        model_id = speaker.tts_model or "eleven_flash_v2_5"
        voice_id = speaker.voice_id
        cfg = dict(speaker.tts_config or {})
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        payload: dict = {"text": text, "model_id": model_id, **cfg}
        headers = {"xi-api-key": api_key, "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.content

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(data)
        logger.debug("ElevenLabs TTS wrote {}", output_file)
        return output_file
