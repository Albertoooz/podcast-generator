"""Resolve EpisodeProfile + libraries into runtime SpeakerProfile."""

from __future__ import annotations

from typing import Any

from app.models.episode import EpisodeProfile
from app.models.speaker import Speaker, SpeakerEntry, SpeakerProfile, SpeakersLibrary
from app.models.voice import VoiceEntry, VoiceLibrary

DEFAULT_TTS_MODEL: dict[str, str] = {
    "openai": "gpt-4o-mini-tts",
    "elevenlabs": "eleven_flash_v2_5",
    "voxtral_cloud": "voxtral-mini-tts-2603",
    "voxtral_local": "voxtral-tts-2603",
    "voxtral_mlx": "voxtral-tts-2603",
    "xtts": "tts_models/multilingual/multi-dataset/xtts_v2",
}

DEFAULT_VOICE_PRESET: dict[str, str] = {
    "openai": "alloy",
    # voxtral_cloud has no preset names; the placeholder is a sentinel so the speaker model
    # field stays non-empty. The provider will only forward a voice_id that looks like a UUID.
    "voxtral_cloud": "mistral_default",
    # vLLM-Omni local server still uses the old preset names from the HF README.
    "voxtral_local": "casual_male",
    "voxtral_mlx": "casual_male",
    "xtts": "alloy",
}


def _default_voice_id_for_provider(prov: str) -> str:
    return DEFAULT_VOICE_PRESET.get(prov, DEFAULT_VOICE_PRESET["openai"])


def _voice_to_speaker_fields(ve: VoiceEntry) -> dict[str, Any]:
    prov = ve.provider.lower().strip()
    model = DEFAULT_TTS_MODEL.get(prov, DEFAULT_TTS_MODEL["openai"])
    vid = ve.provider_voice_id
    if prov in ("voxtral_cloud", "voxtral_local", "voxtral_mlx") and not (vid and str(vid).strip()):
        vid = DEFAULT_VOICE_PRESET.get(prov, "mistral_default")
    if not vid:
        raise ValueError(f"Voice '{ve.label}' (provider={prov}) is missing provider_voice_id")
    return {
        "voice_id": vid.strip(),
        "voice_sample_path": ve.sample_path,
        "tts_provider": prov,
        "tts_model": model,
        "tts_config": None,
    }


def _entry_to_speaker(
    se: SpeakerEntry,
    voices: VoiceLibrary,
) -> Speaker:
    if not se.voice_ref:
        prov = (se.tts_provider or "openai").lower().strip()
        model = (se.tts_model or "").strip() or DEFAULT_TTS_MODEL.get(
            prov,
            DEFAULT_TTS_MODEL["openai"],
        )
        preset_in = (se.tts_voice_preset or "").strip()
        if prov == "elevenlabs" and not preset_in:
            raise ValueError(
                f"Speaker '{se.name}': ElevenLabs needs a voice id — pick a Voice from the "
                "library or set TTS voice / preset to your ElevenLabs voice id.",
            )
        vid = preset_in or _default_voice_id_for_provider(prov)
        return Speaker(
            name=se.name,
            voice_id=vid,
            backstory=se.backstory or "Podcast participant.",
            personality=se.personality or "Engaging",
            style_description=se.style_description,
            avatar_path=se.avatar_path,
            tts_provider=prov,
            tts_model=model,
        )
    if se.voice_ref not in voices.voices:
        raise ValueError(f"Unknown voice_ref '{se.voice_ref}' for speaker entry")
    ve = voices.voices[se.voice_ref]
    vf = _voice_to_speaker_fields(ve)
    return Speaker(
        name=se.name,
        backstory=se.backstory,
        personality=se.personality,
        style_description=se.style_description or ve.style_description,
        avatar_path=se.avatar_path,
        **vf,
    )


def resolve_speakers(
    episode: EpisodeProfile,
    speakers_lib: SpeakersLibrary,
    voices_lib: VoiceLibrary,
) -> SpeakerProfile:
    """Build SpeakerProfile from episode.speakers library ids."""
    if not episode.speakers:
        raise ValueError("episode.speakers is empty")
    ids = episode.speakers
    if not (1 <= len(ids) <= 4):
        raise ValueError("Episode must reference 1–4 speakers from the library")
    built: list[Speaker] = []
    for sid in ids:
        if sid not in speakers_lib.speakers:
            raise ValueError(f"Speaker library id not found: {sid}")
        built.append(_entry_to_speaker(speakers_lib.speakers[sid], voices_lib))

    first = built[0]
    fp = first.tts_provider or "openai"
    fm = first.tts_model or DEFAULT_TTS_MODEL.get(fp, DEFAULT_TTS_MODEL["openai"])
    return SpeakerProfile(
        tts_provider=fp,
        tts_model=fm,
        speakers=built,
        tts_config=None,
    )


def resolve_episode_to_speaker_profile(
    episode: EpisodeProfile,
    *,
    speakers_lib: SpeakersLibrary,
    voices_lib: VoiceLibrary,
) -> SpeakerProfile:
    """Resolve ``episode.speakers`` library ids into a runtime ``SpeakerProfile``."""
    if episode.speakers:
        return resolve_speakers(episode, speakers_lib, voices_lib)
    raise ValueError(
        "Episode profile must set `speakers` to 1–4 ids from the speakers library "
        "(configs/speakers_library.json). Pick speakers in the Episodes UI or edit JSON."
    )
