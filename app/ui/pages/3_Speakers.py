"""Speakers library — grid tiles and editor (configs/speakers_library.json)."""

from __future__ import annotations

import asyncio
import importlib.util
import uuid
from pathlib import Path

_b = Path(__file__).resolve().parent.parent / "_bootstrap.py"
_s = importlib.util.spec_from_file_location("podcast_streamlit_bootstrap", _b)
if _s and _s.loader:
    _mod = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(_mod)

import streamlit as st  # noqa: E402

from app.config_loader import load_speakers_library, save_speakers_library  # noqa: E402
from app.models.speaker import SpeakerEntry, SpeakersLibrary  # noqa: E402
from app.services.speaker_resolver import DEFAULT_TTS_MODEL  # noqa: E402
from app.tts.providers.voxtral_cloud import list_voices_on_mistral  # noqa: E402
from app.tts.registry import list_tts_provider_ids  # noqa: E402
from app.tts.voice_library import list_voices  # noqa: E402
from app.ui._avatar_store import save_avatar  # noqa: E402

st.header("Speakers")
st.caption("Global speaker personas linked to entries in the Voice library.")

if "sp_view" not in st.session_state:
    st.session_state.sp_view = "grid"
if "sp_edit_id" not in st.session_state:
    st.session_state.sp_edit_id = None


def _back_to_grid() -> None:
    st.session_state.sp_view = "grid"
    st.session_state.sp_edit_id = None


lib = load_speakers_library()
ids = sorted(lib.speakers.keys())

if st.session_state.sp_view == "edit" and st.session_state.sp_edit_id:
    sid = st.session_state.sp_edit_id
    if sid not in lib.speakers:
        st.error("Speaker not found")
        _back_to_grid()
        st.stop()
    entry = lib.speakers[sid]
    if st.button("← Back to grid"):
        _back_to_grid()
        st.rerun()

    st.subheader(f"Edit: `{sid}`")
    name = st.text_input("Display name", value=entry.name, key="se_name")
    short_bio = st.text_input("Short bio (tile)", value=entry.short_bio, key="se_short")
    backstory = st.text_area("Backstory", value=entry.backstory, key="se_back")
    personality = st.text_area("Personality", value=entry.personality, key="se_pers")
    style = st.text_area("Style description", value=entry.style_description, key="se_style")
    vopts = ["(none)"] + list_voices()
    cur_v = entry.voice_ref or "(none)"
    if cur_v not in vopts:
        vopts = [cur_v] + vopts
    vidx = vopts.index(cur_v) if cur_v in vopts else 0
    voice_sel = st.selectbox("Voice from library", vopts, index=vidx, key="se_voice")

    tts_prov_ids = list_tts_provider_ids()
    if voice_sel == "(none)":
        st.caption("No library voice — choose TTS provider and optional preset below.")
        _tp = (entry.tts_provider or "openai").lower().strip()
        _pidx = tts_prov_ids.index(_tp) if _tp in tts_prov_ids else 0
        tts_p = st.selectbox(
            "TTS provider",
            tts_prov_ids,
            index=_pidx,
            key=f"se_tts_p_{sid}",
        )
        st.text_input(
            "TTS model (optional)",
            value=entry.tts_model or "",
            key=f"se_tts_m_{sid}",
            help="Leave empty to use the default model for this provider.",
            placeholder=DEFAULT_TTS_MODEL.get(tts_p, ""),
        )
        mistral_list_key = f"se_mistral_voices_{sid}"
        if tts_p == "voxtral_cloud":
            st.markdown("**Mistral cloud — saved voice**")
            r1, r2 = st.columns([1, 2])
            with r1:
                if st.button("Fetch from Mistral", key=f"se_mistral_fetch_{sid}"):
                    try:
                        st.session_state[mistral_list_key] = asyncio.run(list_voices_on_mistral())
                    except Exception as exc:
                        st.session_state[mistral_list_key] = []
                        st.session_state[f"se_mistral_err_{sid}"] = str(exc)
            with r2:
                err = st.session_state.pop(f"se_mistral_err_{sid}", None)
                if err:
                    st.error(err)
            remote: list[dict] = st.session_state.get(mistral_list_key) or []
            if remote:
                ids_only = [str(v["id"]) for v in remote]
                name_by_id: dict[str, str] = {}
                for v in remote:
                    vid = str(v["id"])
                    nm = (v.get("name") or "").strip() or vid[:8]
                    name_by_id[vid] = nm

                def _fmt_voice(vid: str) -> str:
                    return f"{name_by_id.get(vid, vid)} — {vid}"

                cur = (entry.tts_voice_preset or "").strip()
                default_ix = ids_only.index(cur) if cur in ids_only else 0
                st.selectbox(
                    "Pick a voice from your Mistral account",
                    ids_only,
                    index=default_ix,
                    format_func=_fmt_voice,
                    key=f"se_mistral_voice_{sid}",
                    help="UUID is stored as TTS voice / preset and sent to Mistral as `voice`.",
                )
            else:
                st.caption("Click **Fetch from Mistral** to list voices, or paste a UUID below.")
            st.text_input(
                "Mistral voice UUID (optional, overrides pick above)",
                value=entry.tts_voice_preset or "",
                key=f"se_tts_vp_{sid}",
                help=(
                    "If set, overrides the dropdown. Paste a UUID from Mistral Studio when needed."
                ),
            )
        else:
            st.text_input(
                "TTS voice / preset (optional)",
                value=entry.tts_voice_preset or "",
                key=f"se_tts_vp_{sid}",
                help=(
                    "Provider-specific voice id (e.g. OpenAI `alloy`). "
                    "ElevenLabs needs your dashboard voice id here without a library voice."
                ),
            )
    else:
        st.caption("TTS provider, model, and sample come from the selected Voice library entry.")

    av = entry.avatar_path or ""
    if av and Path(av).exists():
        st.image(av, width=160)
    up = st.file_uploader("Avatar image", type=["png", "jpg", "jpeg", "webp"])
    if up is not None:
        p = save_avatar(up, sid)
        av = str(p)

    apath = st.text_input("Avatar path", value=av, key="se_avatar")

    if st.button("Save speaker", type="primary"):
        vr = None if voice_sel == "(none)" else voice_sel
        if vr is None:
            tm_raw = (st.session_state.get(f"se_tts_m_{sid}") or "").strip()
            tvp_raw = (st.session_state.get(f"se_tts_vp_{sid}") or "").strip()
            tts_p_save = (st.session_state.get(f"se_tts_p_{sid}") or "openai").lower().strip()
            mistral_list_key = f"se_mistral_voices_{sid}"
            if tts_p_save == "voxtral_cloud" and tvp_raw:
                tts_voice_final = tvp_raw
            elif tts_p_save == "voxtral_cloud" and st.session_state.get(mistral_list_key):
                tts_voice_final = (
                    str(st.session_state.get(f"se_mistral_voice_{sid}") or "").strip() or None
                )
            else:
                tts_voice_final = tvp_raw or None
            new_e = SpeakerEntry(
                name=name,
                short_bio=short_bio,
                backstory=backstory,
                personality=personality,
                style_description=style,
                voice_ref=None,
                tts_provider=st.session_state.get(f"se_tts_p_{sid}", "openai"),
                tts_model=tm_raw or None,
                tts_voice_preset=tts_voice_final,
                avatar_path=apath.strip() or None,
            )
        else:
            new_e = SpeakerEntry(
                name=name,
                short_bio=short_bio,
                backstory=backstory,
                personality=personality,
                style_description=style,
                voice_ref=vr,
                tts_provider=None,
                tts_model=None,
                tts_voice_preset=None,
                avatar_path=apath.strip() or None,
            )
        speakers = dict(lib.speakers)
        speakers[sid] = new_e
        save_speakers_library(SpeakersLibrary(speakers=speakers))
        st.success("Saved")
        _back_to_grid()
        st.rerun()

    st.stop()

# --- grid ---
st.subheader("All speakers")
if st.button("+ New speaker"):
    nid = f"speaker_{uuid.uuid4().hex[:8]}"
    speakers = dict(lib.speakers)
    speakers[nid] = SpeakerEntry(
        name="New speaker",
        short_bio="",
        backstory="",
        personality="",
        style_description="",
        voice_ref=None,
    )
    save_speakers_library(SpeakersLibrary(speakers=speakers))
    st.session_state.sp_view = "edit"
    st.session_state.sp_edit_id = nid
    st.rerun()

if not ids:
    st.info("No speakers yet — create one above.")
    st.stop()

n_cols = 3
for row_start in range(0, len(ids), n_cols):
    cols = st.columns(n_cols)
    for j in range(n_cols):
        idx = row_start + j
        if idx >= len(ids):
            break
        sid = ids[idx]
        e = lib.speakers[sid]
        with cols[j]:
            with st.container(border=True):
                ap = e.avatar_path
                if ap and Path(ap).exists():
                    st.image(ap, use_container_width=True)
                else:
                    st.caption("No avatar")
                st.markdown(f"### {e.name}")
                st.caption(e.short_bio or "—")
                if e.voice_ref:
                    st.caption(f"voice: `{e.voice_ref}`")
                else:
                    st.caption(f"no library voice · TTS: `{e.tts_provider or 'openai'}`")
                if st.button("Edit", key=f"ed_{sid}"):
                    st.session_state.sp_view = "edit"
                    st.session_state.sp_edit_id = sid
                    st.rerun()
                if st.button("Delete", key=f"dl_{sid}"):
                    speakers = dict(lib.speakers)
                    del speakers[sid]
                    save_speakers_library(SpeakersLibrary(speakers=speakers))
                    st.rerun()
