"""Apple Silicon MLX inference via the third-party Voxtral MLX port (Mistral-TTS-iOS)."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import threading
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from pydub import AudioSegment

from app.models.speaker import Speaker
from app.settings import get_settings

_lock = threading.Lock()
_loaded: tuple[Any, Any, str] | None = None


def _ensure_sys_path(root: str) -> None:
    r = Path(root).resolve()
    s = str(r)
    if s not in sys.path:
        sys.path.insert(0, s)


def _get_model_and_tokenizer() -> tuple[Any, Any]:
    global _loaded
    settings = get_settings()
    root = settings.voxtral_mlx_root
    model_path = settings.voxtral_mlx_model_path
    if not root or not model_path:
        raise ValueError(
            "VOXTRAL_MLX_ROOT and VOXTRAL_MLX_MODEL_PATH must be set for voxtral_mlx "
            "(see docs/voxtral-local-setup.md)."
        )
    resolved = str(Path(model_path).expanduser().resolve())
    with _lock:
        if _loaded is not None and _loaded[2] == resolved:
            return _loaded[0], _loaded[1]
        if importlib.util.find_spec("mlx") is None:
            raise RuntimeError(
                "MLX is not installed. On Apple Silicon: uv sync --extra mlx "
                "(or install mlx, mistral-common, safetensors, torch, soundfile in this env)."
            )
        _ensure_sys_path(root)
        from voxtral_tts.voxtral_tts import load

        logger.info("Loading MLX Voxtral from {}", resolved)
        model, tokenizer = load(resolved)
        _loaded = (model, tokenizer, resolved)
        return model, tokenizer


def _resolve_voice(speaker: Speaker) -> str | None:
    for key in (speaker.voice_sample_path, speaker.voice_id):
        if not key:
            continue
        p = Path(key).expanduser()
        if p.is_file() and p.suffix.lower() == ".pt":
            return str(p.resolve())
    return speaker.voice_id or None


def _synthesize_sync(text: str, speaker: Speaker, output_file: Path) -> Path:
    model, tokenizer = _get_model_and_tokenizer()
    cfg = dict(speaker.tts_config or {})
    temperature = float(cfg.pop("temperature", 0.0))
    top_p = float(cfg.pop("top_p", 1.0))
    max_audio_frames = int(cfg.pop("max_audio_frames", 2048))
    repetition_penalty = float(cfg.pop("repetition_penalty", 1.1))
    verbose = bool(cfg.pop("verbose", False))

    voice = _resolve_voice(speaker)
    wav_tmp = output_file.with_suffix(".wav.tmp")
    try:
        with _lock:
            last = None
            for gr in model.generate(
                text,
                tokenizer=tokenizer,
                voice=voice,
                temperature=temperature,
                top_p=top_p,
                max_audio_frames=max_audio_frames,
                repetition_penalty=repetition_penalty,
                verbose=verbose,
                **cfg,
            ):
                last = gr
            if last is None:
                raise RuntimeError("MLX Voxtral produced no audio")

        audio_np = np.array(last.audio, dtype=np.float32).reshape(-1)
        peak = float(np.max(np.abs(audio_np))) or 1.0
        if peak > 1.0:
            audio_np = audio_np / peak
        audio_i16 = (audio_np * 32767.0).clip(-32768, 32767).astype(np.int16)

        import soundfile as sf

        sf.write(str(wav_tmp), audio_i16, int(last.sample_rate), subtype="PCM_16")

        output_file.parent.mkdir(parents=True, exist_ok=True)
        seg = AudioSegment.from_wav(str(wav_tmp))
        if output_file.suffix.lower() == ".mp3":
            seg.export(str(output_file), format="mp3")
        else:
            seg.export(str(output_file), format=output_file.suffix.lstrip(".") or "wav")

        logger.debug("Voxtral MLX TTS wrote {}", output_file)
        return output_file
    finally:
        if wav_tmp.exists():
            wav_tmp.unlink(missing_ok=True)


class VoxtralMLXProvider:
    name = "voxtral_mlx"

    async def synthesize(self, text: str, speaker: Speaker, output_file: Path) -> Path:
        return await asyncio.to_thread(_synthesize_sync, text, speaker, output_file)
