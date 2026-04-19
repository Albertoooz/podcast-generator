"""OpenAI-compatible audio/speech endpoint on local vLLM Omni (Voxtral)."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from app.models.speaker import Speaker
from app.settings import get_settings


class VoxtralLocalProvider:
    name = "voxtral_local"

    async def synthesize(self, text: str, speaker: Speaker, output_file: Path) -> Path:
        settings = get_settings()
        base = settings.voxtral_local_url.rstrip("/")
        url = f"{base}/v1/audio/speech"
        model = speaker.tts_model or "mistralai/Voxtral-4B-TTS-2603"
        extra: dict[str, Any] = dict(speaker.tts_config or {})

        payload: dict[str, Any] = {
            "model": model,
            "input": text,
            "voice": speaker.voice_id,
            **extra,
        }

        if speaker.style_description:
            payload.setdefault("style", speaker.style_description)

        sample_path = speaker.voice_sample_path
        if sample_path:
            p = Path(sample_path).expanduser()
            if p.is_file():
                b64 = base64.standard_b64encode(p.read_bytes()).decode("ascii")
                payload["voice_reference"] = b64

        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.content

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(data)
        logger.debug("Voxtral local TTS wrote {}", output_file)
        return output_file
