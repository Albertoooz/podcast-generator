from __future__ import annotations

import pytest

from app.models.episode import EpisodeProfile
from app.models.speaker import Speaker, SpeakerEntry, SpeakerProfile, SpeakersLibrary
from app.models.voice import VoiceEntry, VoiceLibrary
from app.services.speaker_resolver import resolve_episode_to_speaker_profile


def test_resolve_without_speakers_raises():
    ep = EpisodeProfile(default_briefing="x", speakers=None)
    with pytest.raises(ValueError, match="speakers"):
        resolve_episode_to_speaker_profile(
            ep,
            speakers_lib=SpeakersLibrary(speakers={}),
            voices_lib=VoiceLibrary(voices={}),
        )


def test_resolve_library():
    ep = EpisodeProfile(
        default_briefing="x",
        speakers=["s1"],
    )
    r = resolve_episode_to_speaker_profile(
        ep,
        speakers_lib=SpeakersLibrary(
            speakers={
                "s1": SpeakerEntry(
                    name="Sam",
                    backstory="b",
                    personality="p",
                    voice_ref="v1",
                ),
            },
        ),
        voices_lib=VoiceLibrary(
            voices={
                "v1": VoiceEntry(
                    label="v",
                    provider="openai",
                    provider_voice_id="nova",
                ),
            },
        ),
    )
    assert r.speakers[0].name == "Sam"
    assert r.speakers[0].voice_id == "nova"


def test_resolve_library_no_voice_custom_tts():
    ep = EpisodeProfile(
        default_briefing="x",
        speakers=["s2"],
    )
    r = resolve_episode_to_speaker_profile(
        ep,
        speakers_lib=SpeakersLibrary(
            speakers={
                "s2": SpeakerEntry(
                    name="Pat",
                    backstory="b",
                    personality="p",
                    voice_ref=None,
                    tts_provider="voxtral_cloud",
                    tts_model="",
                    tts_voice_preset="",
                ),
            },
        ),
        voices_lib=VoiceLibrary(voices={}),
    )
    assert r.speakers[0].tts_provider == "voxtral_cloud"
    assert r.speakers[0].voice_id == "mistral_default"


def test_elevenlabs_no_voice_requires_preset():
    ep = EpisodeProfile(
        default_briefing="x",
        speakers=["s3"],
    )
    with pytest.raises(ValueError, match="ElevenLabs"):
        resolve_episode_to_speaker_profile(
            ep,
            speakers_lib=SpeakersLibrary(
                speakers={
                    "s3": SpeakerEntry(
                        name="Eli",
                        backstory="b",
                        personality="p",
                        voice_ref=None,
                        tts_provider="elevenlabs",
                    ),
                },
            ),
            voices_lib=VoiceLibrary(voices={}),
        )


def test_speaker_profile_allows_duplicate_voice_preset():
    """Multiple hosts may share the same voice_id placeholder for Voxtral cloud."""
    sp = SpeakerProfile(
        tts_provider="voxtral_cloud",
        tts_model="voxtral-mini-tts-2603",
        speakers=[
            Speaker(name="Host A", voice_id="mistral_default", backstory="a", personality="a"),
            Speaker(name="Host B", voice_id="mistral_default", backstory="b", personality="b"),
        ],
    )
    assert sp.speakers[0].voice_id == sp.speakers[1].voice_id


def test_elevenlabs_voice_requires_id():
    with pytest.raises(Exception):
        VoiceEntry(label="x", provider="elevenlabs", provider_voice_id=None)
