import asyncio
from pathlib import Path
from typing import Any

from langchain_core.runnables import RunnableConfig
from loguru import logger
from pydub import AudioSegment

from app.graph.state import PodcastState


async def combine_audio_node(state: PodcastState, config: RunnableConfig) -> dict[str, Any]:
    clips_dir = state["output_dir"] / "clips"
    audio_dir = state["output_dir"] / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    final_name = f"{state['episode_name']}.mp3"
    out_path = audio_dir / final_name

    files = sorted(clips_dir.glob("*.mp3"))
    if not files:
        logger.error("No clips to combine in {}", clips_dir)
        return {"final_output_file_path": None}

    def _combine() -> Path:
        combined = AudioSegment.empty()
        for f in files:
            combined += AudioSegment.from_mp3(str(f))
        combined.export(str(out_path), format="mp3")
        return out_path

    out = await asyncio.to_thread(_combine)
    logger.info("Combined audio: {}", out)
    return {"final_output_file_path": out}
