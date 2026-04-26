"""Voice library: register voices with a target TTS provider (metadata only)."""

from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path

_b = Path(__file__).resolve().parent.parent / "_bootstrap.py"
_s = importlib.util.spec_from_file_location("podcast_streamlit_bootstrap", _b)
if _s and _s.loader:
    _mod = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(_mod)

import asyncio  # noqa: E402

import streamlit as st  # noqa: E402

from app.tts.providers.elevenlabs import (  # noqa: E402
    delete_voice_on_elevenlabs,
    elevenlabs_voice_id_looks_assigned,
    format_elevenlabs_user_error,
    list_voices_on_elevenlabs,
    register_voice_with_elevenlabs,
)
from app.tts.providers.voxtral_cloud import (  # noqa: E402
    _is_mistral_voice_uuid,
    delete_voice_on_mistral,
    list_voices_on_mistral,
    register_voice_with_mistral,
)
from app.tts.registry import list_tts_provider_ids  # noqa: E402
from app.tts.voice_library import (  # noqa: E402
    add_voice,
    get_voice,
    list_voices,
    remove_voice,
    update_voice,
    voices_dir,
)

SCRIPT_LANG_TO_CODE: dict[str, str] = {"English": "en", "Polski": "pl"}

READING_SCRIPTS: dict[str, str] = {
    "English": (
        "I'm recording audio to clone my voice. Once done, I'll be able to generate speech "
        "that sounds just like me. It's incredible how AI can capture the way I talk: my tone, "
        "my rhythm, even the little quirks that make my voice unique. I can't wait to hear it!"
    ),
    "Polski": (
        "Nagrywam teraz próbkę głosu, żeby go sklonować. Potem będę mógł wygenerować mowę, "
        "która brzmi dokładnie jak ja. To niesamowite, jak sztuczna inteligencja potrafi oddać "
        "sposób, w jaki mówię: mój ton, rytm, a nawet drobne dziwactwa, które czynią mój głos "
        "wyjątkowym. Nie mogę się doczekać, aż go usłyszę!"
    ),
}

st.header("Voice library")
st.caption(
    "Stores metadata locally. For **Mistral / Voxtral cloud**: upload a sample, then "
    "**Register with Mistral** — the UUID is saved as *Provider voice id*. "
    "For **ElevenLabs**: use **Fetch from ElevenLabs** to see account voices, or upload a sample "
    "and **Register with ElevenLabs** (instant clone) to get a `voice_id`. "
    "You can also paste an existing ElevenLabs voice id from their dashboard."
)

voices_dir().mkdir(parents=True, exist_ok=True)

st.subheader("Register a new voice")
label_in = st.text_input("Label", placeholder="My narrator voice")
prov = st.selectbox("Target TTS provider", list_tts_provider_ids())

preset_in = st.text_input(
    "Provider voice id / preset (OpenAI required; ElevenLabs: leave empty if you upload a sample)",
    placeholder="Leave empty for ElevenLabs + sample, then use IVC on the tile below",
)

st.markdown("**Voice sample** — record yourself or upload a file (browser must allow microphone).")
script_lang = st.selectbox(
    "Reading script language",
    list(READING_SCRIPTS.keys()),
    index=0,
    help="Read this text aloud while recording for a consistent cloning sample.",
)
with st.container(border=True):
    st.markdown(f"_{READING_SCRIPTS[script_lang]}_")

recorded = st.audio_input(
    "Record (read the script above)",
    key="vl_mic_sample",
    help="Uses your microphone. Re-record if you need another take.",
)

uploaded = st.file_uploader(
    (
        "Or upload reference audio (WAV/MP3) — required for XTTS/MLX/local Voxtral "
        "if you don't record; optional for Mistral cloud if you set a preset above"
    ),
    type=["wav", "mp3"],
)
if recorded is not None and uploaded is not None:
    st.caption("Both recording and file are set — **recording** will be used when you save.")

style = st.text_area("Style / delivery notes", height=80)
language = st.text_input("Language code (optional)", placeholder="en")
key_in = st.text_input("Library key (optional)", placeholder="my_voice")


def _write_sample_from_mic_or_file() -> Path | None:
    """Prefer microphone recording over file upload."""
    # Prefer the widget return value; session_state can lag on some Streamlit versions.
    mic = recorded if recorded is not None else st.session_state.get("vl_mic_sample")
    if mic is not None:
        raw = mic.getvalue()
        if raw:
            ext = Path(mic.name).suffix.lower() if getattr(mic, "name", None) else ""
            if ext not in (".wav", ".webm", ".mp3", ".ogg", ".m4a", ".mp4"):
                ext = ".wav"
            out = voices_dir() / f"record_{uuid.uuid4().hex[:10]}{ext}"
            out.write_bytes(raw)
            return out
    if uploaded is not None:
        ext = Path(uploaded.name).suffix or ".wav"
        path = voices_dir() / f"upload_{key_in or 'sample'}{ext}"
        path.write_bytes(uploaded.getvalue())
        return path
    return None


def _validate_and_save() -> None:
    if not label_in.strip():
        st.error("Label is required")
        return
    p = prov.lower().strip()
    pid = preset_in.strip() if preset_in else ""
    path = _write_sample_from_mic_or_file()
    if p == "openai" and not pid:
        st.error("Provider voice id / preset is required for OpenAI")
        return
    if p == "elevenlabs" and not pid and path is None:
        st.error("ElevenLabs: provide a voice id and/or a voice sample (clone after save via tile)")
        return
    if p in ("xtts", "voxtral_mlx", "voxtral_local") and path is None:
        st.error("Upload a sample for this provider")
        return
    if p == "voxtral_cloud" and not pid and path is None:
        st.error("Provide a Mistral preset id and/or a sample file")
        return
    lang_resolved = language.strip() or SCRIPT_LANG_TO_CODE.get(script_lang) or None
    try:
        vid = add_voice(
            label_in.strip(),
            prov,
            provider_voice_id=pid or None,
            sample_path=path,
            style_description=style,
            language=lang_resolved,
            voice_id=key_in.strip() or None,
        )
    except Exception as e:
        st.exception(e)
    else:
        st.success(f"Registered: **{vid}**")
        st.rerun()


if st.button("Save voice", type="primary"):
    _validate_and_save()

st.subheader("Registered voices")

# --- Mistral "browse remote voices" expander -----------------------------------
with st.expander("☁️ Browse voices registered on Mistral", expanded=False):
    if st.button("Fetch from Mistral", key="vl_fetch_mistral"):
        try:
            remote = asyncio.run(list_voices_on_mistral())
            st.session_state["vl_mistral_remote"] = remote
        except Exception as exc:
            st.error(f"Could not fetch: {exc}")

    remote_voices: list[dict] = st.session_state.get("vl_mistral_remote", [])
    if remote_voices:
        st.caption(f"{len(remote_voices)} voice(s) found on Mistral:")
        for rv in remote_voices:
            st.markdown(
                f"- **{rv.get('name', '?')}** &mdash; `{rv['id']}`  "
                f"<small>created {rv.get('created_at', '')[:10]}</small>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("Click **Fetch from Mistral** to see your remote voices.")

with st.expander("☁️ Browse voices on ElevenLabs", expanded=False):
    if st.button("Fetch from ElevenLabs", key="vl_fetch_eleven"):
        try:
            el_remote = asyncio.run(list_voices_on_elevenlabs())
            st.session_state["vl_eleven_remote"] = el_remote
        except Exception as exc:
            st.error(f"Could not fetch: {format_elevenlabs_user_error(exc)}")

    el_voices: list[dict] = st.session_state.get("vl_eleven_remote", [])
    if el_voices:
        st.caption(f"{len(el_voices)} voice(s) on ElevenLabs:")
        for rv in el_voices:
            cat = rv.get("category") or "—"
            st.markdown(
                f"- **{rv.get('name', '?')}** (`{cat}`) &mdash; `{rv['id']}`",
                unsafe_allow_html=True,
            )
    else:
        st.caption(
            "Click **Fetch from ElevenLabs** to list premade and cloned voices. "
            "Restricted API keys need Voices: Read (see ElevenLabs → API keys)."
        )

# --- Per-voice tiles -----------------------------------------------------------
vids = list_voices()
if not vids:
    st.info("No voices yet.")
else:
    for vid in vids:
        meta = get_voice(vid) or {}
        sample = meta.get("sample_path", "")
        provider = meta.get("provider", "")
        current_pvid = meta.get("provider_voice_id") or ""
        is_mistral = provider == "voxtral_cloud"
        is_eleven = provider == "elevenlabs"
        has_sample = sample and Path(sample).exists()
        is_registered = is_mistral and _is_mistral_voice_uuid(current_pvid)
        el_has_id = is_eleven and elevenlabs_voice_id_looks_assigned(current_pvid)
        el_placeholder_pvid = (
            is_eleven
            and bool((current_pvid or "").strip())
            and not elevenlabs_voice_id_looks_assigned(current_pvid)
        )

        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown(f"### `{vid}`")
                st.caption(f"**{meta.get('label', '')}** · `{provider}`")
                if has_sample:
                    st.audio(sample)
                else:
                    st.caption("No local sample")

                # Mistral registration status + actions
                if is_mistral:
                    if is_registered:
                        st.success("☁️ Registered on Mistral")
                        st.code(current_pvid, language=None)
                        if st.button(
                            "🗑 Delete from Mistral",
                            key=f"vl_mist_del_{vid}",
                            type="secondary",
                        ):
                            try:
                                asyncio.run(delete_voice_on_mistral(current_pvid))
                                update_voice(vid, provider_voice_id=None)
                                st.success("Deleted from Mistral and UUID cleared.")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Delete failed: {exc}")
                    else:
                        if has_sample:
                            if st.button(
                                "☁️ Register with Mistral",
                                key=f"vl_mist_reg_{vid}",
                                type="primary",
                            ):
                                try:
                                    uuid_str = asyncio.run(
                                        register_voice_with_mistral(
                                            meta.get("label") or vid,
                                            sample,
                                            languages=(
                                                [meta["language"]] if meta.get("language") else None
                                            ),
                                        )
                                    )
                                    update_voice(vid, provider_voice_id=uuid_str)
                                    st.success(f"Registered! UUID: `{uuid_str}`")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Registration failed: {exc}")
                        else:
                            st.warning("Upload a sample to register with Mistral.")

                if is_eleven:
                    if el_placeholder_pvid:
                        st.warning(
                            "Provider voice id looks like a placeholder (e.g. the word "
                            "'elevenlabs'), not a real ElevenLabs voice id. Use "
                            "**Register with ElevenLabs (IVC)** below, or clear the field and Save."
                        )
                    if el_has_id:
                        st.success("☁️ ElevenLabs voice id")
                        st.code(current_pvid, language=None)
                        if st.button(
                            "🗑 Delete from ElevenLabs",
                            key=f"vl_el_del_{vid}",
                            type="secondary",
                            help=(
                                "Only for voices you created (cloned). "
                                "Premade voices cannot be removed."
                            ),
                        ):
                            try:
                                asyncio.run(delete_voice_on_elevenlabs(current_pvid.strip()))
                                update_voice(vid, provider_voice_id=None)
                                st.success("Deleted from ElevenLabs; id cleared.")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Delete failed: {format_elevenlabs_user_error(exc)}")
                    else:
                        if has_sample:
                            if st.button(
                                "☁️ Register with ElevenLabs (IVC)",
                                key=f"vl_el_reg_{vid}",
                                type="primary",
                            ):
                                try:
                                    el_id = asyncio.run(
                                        register_voice_with_elevenlabs(
                                            meta.get("label") or vid,
                                            sample,
                                            description=(meta.get("style_description") or "")[:500]
                                            or None,
                                        )
                                    )
                                    update_voice(vid, provider_voice_id=el_id)
                                    st.success(f"Cloned on ElevenLabs: `{el_id}`")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(
                                        f"Registration failed: {format_elevenlabs_user_error(exc)}"
                                    )
                        else:
                            st.warning(
                                "Upload a WAV/MP3 sample to clone on ElevenLabs, "
                                "or paste a voice id."
                            )

            with c2:
                nl = st.text_input("Label", value=meta.get("label", ""), key=f"vl_lab_{vid}")
                np = st.text_input(
                    "Provider voice id / UUID",
                    value=current_pvid,
                    key=f"vl_pvid_{vid}",
                    help=(
                        "Mistral: **Register with Mistral** fills a UUID. "
                        "ElevenLabs: paste a dashboard id, or **Register with ElevenLabs** "
                        "after saving with a sample. OpenAI: e.g. `alloy`."
                    ),
                )
                ns = st.text_area(
                    "Style",
                    value=meta.get("style_description", ""),
                    height=60,
                    key=f"vl_style_{vid}",
                )
                nlng = st.text_input(
                    "Language",
                    value=meta.get("language") or "",
                    key=f"vl_lang_{vid}",
                )
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("Save", key=f"vl_save_{vid}"):
                        update_voice(
                            vid,
                            label=nl,
                            provider_voice_id=np if np.strip() else None,
                            style_description=ns,
                            language=nlng if nlng.strip() else "",
                        )
                        st.success("Updated")
                        st.rerun()
                with b2:
                    if st.button("Delete", type="secondary", key=f"vl_del_{vid}"):
                        remove_voice(vid)
                        st.rerun()
