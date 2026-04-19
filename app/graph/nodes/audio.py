import asyncio
import os
from pathlib import Path
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.graph.state import PodcastState
from app.models.speaker import Speaker
from app.retry import create_retry_decorator, get_retry_config
from app.settings import get_settings
from app.tts.registry import get_tts_provider


def _merge_tts_config(profile_cfg: dict | None, speaker_cfg: dict | None) -> dict:
    if speaker_cfg is not None:
        return dict(speaker_cfg)
    return dict(profile_cfg or {})


def _check_tts_credentials(prov_name: str) -> None:
    """Raise a clear error before the first TTS call when a required key is missing."""
    s = get_settings()
    missing: str | None = None
    if prov_name == "openai" and not s.openai_api_key:
        missing = "OPENAI_API_KEY"
    elif prov_name in ("voxtral_cloud",) and not s.mistral_api_key:
        missing = "MISTRAL_API_KEY"
    elif prov_name == "elevenlabs" and not s.elevenlabs_api_key:
        missing = "ELEVENLABS_API_KEY"
    if missing:
        raise ValueError(
            f"TTS provider '{prov_name}' requires {missing} — add it to your .env file."
        )


async def _synthesize_one(
    text: str,
    speaker: Speaker,
    profile_provider: str,
    profile_model: str,
    output_file: Path,
) -> Path:
    prov_name = speaker.tts_provider or profile_provider
    model = speaker.tts_model or profile_model
    _check_tts_credentials(prov_name)
    # ensure model on speaker for providers that read speaker.tts_model
    sp = speaker.model_copy(update={"tts_model": model})
    provider = get_tts_provider(prov_name)
    return await provider.synthesize(text, sp, output_file)


async def generate_all_audio_node(state: PodcastState, config: RunnableConfig) -> dict[str, Any]:
    transcript = state["transcript"]
    output_dir = state["output_dir"]
    sp = state["speaker_profile"]
    assert sp is not None

    settings = get_settings()
    batch_size = int(os.getenv("TTS_BATCH_SIZE", str(settings.tts_batch_size)))

    tts_provider = sp.tts_provider
    tts_model = sp.tts_model
    profile_cfg = sp.tts_config

    configurable = config.get("configurable") or {}
    retry_cfg = get_retry_config(configurable)
    tts_retry = create_retry_decorator(**retry_cfg)

    @tts_retry
    async def _clip(text: str, speaker: Speaker, path: Path) -> Path:
        merged_cfg = _merge_tts_config(profile_cfg, speaker.tts_config)
        sp_eff = speaker.model_copy(update={"tts_config": merged_cfg})
        return await _synthesize_one(text, sp_eff, tts_provider, tts_model, path)

    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    all_paths: list[Path] = []

    total = len(transcript)
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        tasks = []
        for i in range(batch_start, batch_end):
            line = transcript[i]
            speaker = sp.get_speaker_by_name(line.speaker)
            out_path = clips_dir / f"{i:04d}.mp3"
            tasks.append(_clip(line.dialogue, speaker, out_path))
        batch_paths = await asyncio.gather(*tasks)
        all_paths.extend(batch_paths)
        if batch_end < total:
            await asyncio.sleep(1)

    return {"audio_clips": all_paths}
