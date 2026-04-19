"""Mistral Voxtral TTS via Mistral API (cloud).

``POST /v1/audio/speech`` docs: https://docs.mistral.ai/api/endpoint/audio/speech
``GET  /v1/audio/voices`` docs: https://docs.mistral.ai/api/endpoint/audio/voices
``POST /v1/audio/voices`` docs: https://docs.mistral.ai/api/endpoint/audio/voices

The live API expects JSON field ``voice`` (saved-voice UUID), **not** ``voice_id``.
Either ``voice`` or ``ref_audio`` must be set on each request.
"""

from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from loguru import logger

from app.models.speaker import Speaker
from app.settings import get_settings

_SUFFIX_TO_RESPONSE_FORMAT: dict[str, str] = {
    ".mp3": "mp3",
    ".wav": "wav",
    ".ogg": "opus",
    ".flac": "flac",
}

# Mistral cloud model id (legacy "voxtral-tts-2603" returns 400).
_DEFAULT_CLOUD_MODEL = "voxtral-mini-tts-2603"

# Mistral voice_id values are UUIDs returned by GET /v1/audio/voices.
# There are no hard-coded preset names — sending an unknown string yields HTTP 404.
_VOICE_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Only keys documented for ``POST /v1/audio/speech`` — extra keys (e.g. OpenAI leftovers)
# cause HTTP 400 from Mistral.
_SPEECH_OPTION_KEYS = frozenset({"model", "ref_audio", "response_format", "stream", "voice"})

# First saved voice UUID on this Mistral account (when speaker has no UUID).
_cached_default_mistral_voice: str | None = None

# Mistral accepts WAV/MP3 for ``ref_audio``; browser mic often saves WebM which yields 400.
_REF_AUDIO_SUFFIXES = frozenset({".wav", ".mp3"})


def _is_mistral_voice_uuid(v: str) -> bool:
    """Return True only if *v* looks like a UUID from GET /v1/audio/voices."""
    return bool(_VOICE_UUID_RE.match((v or "").strip()))


def _normalize_cloud_model(name: str | None) -> str:
    n = (name or "").strip()
    if not n or n == "voxtral-tts-2603":
        return _DEFAULT_CLOUD_MODEL
    return n


def _speech_model_for_api(name: str | None) -> str:
    """Return a model id Mistral accepts; fall back if *name* is empty or not Voxtral-shaped."""
    n = _normalize_cloud_model(name)
    if "voxtral" not in n.lower():
        logger.warning(
            "voxtral_cloud: TTS model {!r} is not a Voxtral id — using {}",
            n,
            _DEFAULT_CLOUD_MODEL,
        )
        return _DEFAULT_CLOUD_MODEL
    return n


def _filter_speech_options(raw: dict[str, Any]) -> dict[str, Any]:
    """Keep only documented ``/audio/speech`` JSON fields (drops LLM / OpenAI noise)."""
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if k in _SPEECH_OPTION_KEYS and v is not None:
            out[k] = v
    dropped = set(raw) - set(out)
    if dropped:
        logger.warning("voxtral_cloud: ignoring unknown TTS config keys: {}", sorted(dropped))
    return out


def _mistral_api_root(base_url: str) -> str:
    """Return the ``/v1`` root from any variant of the configured base URL."""
    u = base_url.strip().rstrip("/")
    if u.endswith("/audio/speech"):
        u = u[: -len("/audio/speech")]
    if u.endswith("/audio/voices"):
        u = u[: -len("/audio/voices")]
    if not u.endswith("/v1"):
        parsed = urlparse(u)
        if parsed.path in ("", "/"):
            u = f"{parsed.scheme}://{parsed.netloc}/v1"
        else:
            u = f"{u}/v1"
    return u


def _mistral_voices_url(base_url: str, voice_id: str | None = None) -> str:
    """Build URL for ``GET/POST /v1/audio/voices`` (or a specific voice sub-path)."""
    root = _mistral_api_root(base_url)
    url = f"{root}/audio/voices"
    if voice_id:
        url = f"{url}/{voice_id}"
    return url


def _mistral_audio_speech_url(base_url: str) -> str:
    """Build ``POST`` URL for Mistral cloud TTS.

    Accepts the usual base (``https://api.mistral.ai/v1``), a bare host
    (``https://api.mistral.ai``), or a **full** speech URL without duplicating
    ``/audio/speech`` (a common cause of HTTP 404).
    """
    root = _mistral_api_root(base_url)
    return f"{root}/audio/speech"


def _decode_response_body(r: httpx.Response) -> bytes:
    """Mistral returns JSON with base64 ``audio_data``; some proxies may return raw bytes."""
    ct = (r.headers.get("content-type") or "").lower()
    if "application/json" in ct or (r.content[:1] in (b"{", b"[")):
        body = r.json()
        if isinstance(body, dict) and "audio_data" in body:
            raw = body["audio_data"]
            if isinstance(raw, str):
                return base64.standard_b64decode(raw)
            raise ValueError("audio_data is not a base64 string")
        hint = list(body) if isinstance(body, dict) else type(body)
        raise ValueError(f"Unexpected JSON from Mistral TTS: keys={hint}")
    return r.content


def _mistral_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


async def register_voice_with_mistral(
    name: str,
    sample_path: str | Path,
    *,
    languages: list[str] | None = None,
    gender: str | None = None,
    age: int | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> str:
    """Upload *sample_path* to Mistral ``POST /v1/audio/voices`` and return the UUID.

    Args:
        name: Display name for the voice (any string).
        sample_path: Path to a WAV or MP3 audio sample (≥ a few seconds).
        languages: Optional list of BCP-47 language codes (e.g. ``["en", "pl"]``).
        gender: Optional ``"male"`` / ``"female"`` hint.
        age: Optional age hint in years.
        api_key: Override ``MISTRAL_API_KEY`` from env.
        base_url: Override ``MISTRAL_TTS_BASE_URL`` from env.

    Returns:
        UUID string that can be stored as ``provider_voice_id`` and used in
        ``POST /v1/audio/speech`` as ``voice_id``.
    """
    settings = get_settings()
    key = api_key or settings.mistral_api_key
    if not key:
        raise ValueError("MISTRAL_API_KEY is not set")
    url = _mistral_voices_url(base_url or settings.mistral_tts_base_url)

    p = Path(sample_path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"Sample not found: {p}")
    b64 = base64.standard_b64encode(p.read_bytes()).decode("ascii")

    payload: dict[str, Any] = {"name": name, "sample_audio": b64, "sample_filename": p.name}
    if languages:
        payload["languages"] = languages
    if gender:
        payload["gender"] = gender
    if age is not None:
        payload["age"] = age

    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, headers=_mistral_headers(key), json=payload)
        if r.is_error:
            logger.error(
                "Mistral POST /audio/voices HTTP {} — body: {}",
                r.status_code,
                (r.text or "")[:4000],
            )
        r.raise_for_status()
        data = r.json()

    voice_id: str = data["id"]
    logger.info("Registered voice '{}' on Mistral → {}", name, voice_id)
    return voice_id


async def list_voices_on_mistral(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch all voices from ``GET /v1/audio/voices`` (paginated, max 1 000).

    Returns list of dicts with ``id``, ``name``, ``created_at``, ``user_id``.
    """
    settings = get_settings()
    key = api_key or settings.mistral_api_key
    if not key:
        raise ValueError("MISTRAL_API_KEY is not set")
    url = _mistral_voices_url(base_url or settings.mistral_tts_base_url)

    results: list[dict[str, Any]] = []
    offset = 0
    limit = 100
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            r = await client.get(
                url,
                headers=_mistral_headers(key),
                params={"limit": limit, "offset": offset},
            )
            r.raise_for_status()
            body = r.json()
            items: list[dict[str, Any]] = body.get("items") or []
            results.extend(items)
            if len(results) >= body.get("total", 0) or not items:
                break
            offset += limit
    return results


async def _resolve_default_mistral_voice_uuid() -> str:
    """Use the first voice returned by ``GET /v1/audio/voices`` when no UUID is configured.

    Mistral's speech endpoint requires ``voice`` or ``ref_audio`` on every call; there is no
    parameterless default. We cache one UUID per process so transcript batches do not refetch.
    """
    global _cached_default_mistral_voice  # noqa: PLW0603
    if _cached_default_mistral_voice:
        return _cached_default_mistral_voice
    items = await list_voices_on_mistral()
    if not items:
        raise ValueError(
            "Mistral cloud TTS requires a saved voice UUID in field `voice`, or `ref_audio`. "
            "You have no voices on this Mistral account — open **Voices**, add a WAV/MP3 sample, "
            "click **Register with Mistral**, then pick that voice for your speaker; "
            "or paste a voice UUID from the Mistral console.",
        )
    _cached_default_mistral_voice = str(items[0]["id"])
    logger.warning(
        "voxtral_cloud: no `voice` UUID on speaker — using first saved Mistral voice {} ({})",
        _cached_default_mistral_voice,
        items[0].get("name"),
    )
    return _cached_default_mistral_voice


async def delete_voice_on_mistral(
    voice_uuid: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
) -> None:
    """Delete a voice from Mistral via ``DELETE /v1/audio/voices/{voice_id}``."""
    settings = get_settings()
    key = api_key or settings.mistral_api_key
    if not key:
        raise ValueError("MISTRAL_API_KEY is not set")
    url = _mistral_voices_url(base_url or settings.mistral_tts_base_url, voice_id=voice_uuid)
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.delete(url, headers=_mistral_headers(key))
        if r.is_error:
            logger.error(
                "Mistral DELETE /audio/voices/{} HTTP {} — body: {}",
                voice_uuid,
                r.status_code,
                (r.text or "")[:2000],
            )
        r.raise_for_status()
    logger.info("Deleted Mistral voice {}", voice_uuid)


class VoxtralCloudProvider:
    name = "voxtral_cloud"

    async def synthesize(self, text: str, speaker: Speaker, output_file: Path) -> Path:
        settings = get_settings()
        if not settings.mistral_api_key:
            raise ValueError("MISTRAL_API_KEY is not set for Voxtral cloud TTS")

        inp = (text or "").strip()
        if not inp:
            raise ValueError("Mistral TTS: empty dialogue text (nothing to synthesize)")

        url = _mistral_audio_speech_url(settings.mistral_tts_base_url)
        logger.debug("Mistral TTS POST {}", url)
        model = _speech_model_for_api(speaker.tts_model)
        raw_cfg: dict[str, Any] = dict(speaker.tts_config or {})

        # Live API uses ``voice`` (UUID). Older configs used ``voice_id``.
        if "voice_id" in raw_cfg and "voice" not in raw_cfg:
            raw_cfg["voice"] = raw_cfg.pop("voice_id")
        if "voice_reference" in raw_cfg and "ref_audio" not in raw_cfg:
            raw_cfg["ref_audio"] = raw_cfg.pop("voice_reference")

        profile_cfg = _filter_speech_options(raw_cfg)

        suffix = output_file.suffix.lower()
        response_format = profile_cfg.pop(
            "response_format",
            _SUFFIX_TO_RESPONSE_FORMAT.get(suffix, "mp3"),
        )
        stream_val = bool(profile_cfg.pop("stream", False))

        payload: dict[str, Any] = {
            "model": model,
            "input": inp,
            "response_format": response_format,
            **profile_cfg,
        }
        if stream_val:
            payload["stream"] = True

        used_ref_audio = False
        sample_path = speaker.voice_sample_path
        if sample_path:
            p = Path(sample_path).expanduser()
            if p.is_file():
                ext = p.suffix.lower()
                if ext not in _REF_AUDIO_SUFFIXES:
                    logger.warning(
                        "voxtral_cloud: ref_audio from {!r} is not supported by Mistral "
                        "(use .wav or .mp3). Skipping sample — using voice_id or default voice.",
                        ext or "(no extension)",
                    )
                else:
                    b64 = base64.standard_b64encode(p.read_bytes()).decode("ascii")
                    payload["ref_audio"] = b64
                    payload.pop("voice", None)
                    used_ref_audio = True

        if not used_ref_audio:
            cfg_voice = payload.get("voice")
            if _is_mistral_voice_uuid(speaker.voice_id):
                payload["voice"] = speaker.voice_id.strip()
            elif isinstance(cfg_voice, str) and _is_mistral_voice_uuid(cfg_voice):
                pass  # keep UUID from ``speaker.tts_config``
            else:
                payload["voice"] = await _resolve_default_mistral_voice_uuid()

        headers = {
            "Authorization": f"Bearer {settings.mistral_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            if r.is_error:
                body = (r.text or "")[:4000]
                logger.error("Mistral TTS HTTP {} — body: {}", r.status_code, body)
                raise RuntimeError(
                    f"Mistral TTS HTTP {r.status_code} for {url}. Response: {body or '(empty)'}",
                ) from None
            data = _decode_response_body(r)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        if suffix not in (".mp3", ".wav", ".ogg", ".flac"):
            output_file = output_file.with_suffix(".mp3")
        output_file.write_bytes(data)
        logger.debug("Voxtral cloud TTS wrote {}", output_file)
        return output_file
