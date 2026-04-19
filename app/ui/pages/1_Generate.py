"""Generate podcast from the UI."""

from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
from typing import Any, cast

_b = Path(__file__).resolve().parent.parent / "_bootstrap.py"
_s = importlib.util.spec_from_file_location("podcast_streamlit_bootstrap", _b)
if _s and _s.loader:
    _mod = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(_mod)

import streamlit as st  # noqa: E402

from app.config_loader import (  # noqa: E402
    list_episode_profile_names,
    load_episode_profile,
    load_speakers_library,
)
from app.graph.workflow import create_podcast  # noqa: E402
from app.services.speaker_resolver import resolve_episode_to_speaker_profile  # noqa: E402
from app.tts.voice_library import load_voice_library  # noqa: E402

LLM_PROVIDERS = ["openai", "anthropic", "mistral", "ollama", "openrouter"]

st.header("Generate podcast")


def _init_gen_state() -> None:
    defaults: dict[str, Any] = {
        "gen_briefing": "",
        "gen_outline_prov": "openai",
        "gen_outline_model": "gpt-4o-mini",
        "gen_tr_prov": "openai",
        "gen_tr_model": "gpt-4o-mini",
        "gen_num_seg": 3,
        "gen_lang": "",
        "gen_outline_cfg": "{}",
        "gen_transcript_cfg": "{}",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_gen_state()

content = st.text_area("Content", height=200, placeholder="Paste source text...")
episode_name = st.text_input("Episode name", value="my_episode")
output_dir = st.text_input("Output directory", value="output/my_episode")

ep_options = [""] + list_episode_profile_names()
ep_val = st.selectbox("Episode profile (required)", ep_options, key="gen_episode_pick")

if ep_val:
    ep = load_episode_profile(ep_val)
    if st.session_state.get("_gen_ep_tracked") != ep_val:
        st.session_state._gen_ep_tracked = ep_val
        st.session_state.gen_briefing = ep.default_briefing
        st.session_state.gen_outline_prov = ep.outline_provider
        st.session_state.gen_outline_model = ep.outline_model
        st.session_state.gen_tr_prov = ep.transcript_provider
        st.session_state.gen_tr_model = ep.transcript_model
        st.session_state.gen_num_seg = ep.num_segments
        st.session_state.gen_lang = ep.language or ""
        st.session_state.gen_outline_cfg = json.dumps(ep.outline_config or {}, indent=2)
        st.session_state.gen_transcript_cfg = json.dumps(ep.transcript_config or {}, indent=2)
else:
    if "_gen_ep_tracked" in st.session_state:
        st.session_state._gen_ep_tracked = None

st.text_area(
    "Briefing",
    key="gen_briefing",
    height=120,
    help="Optional: overrides the episode profile default_briefing when non-empty.",
)

if ep_val:
    st.subheader("Resolved speakers (read-only)")
    try:
        prev = resolve_episode_to_speaker_profile(
            load_episode_profile(ep_val),
            speakers_lib=load_speakers_library(),
            voices_lib=load_voice_library(),
        )
        n = len(prev.speakers)
        cols = st.columns(min(4, max(1, n)))
        for i, s in enumerate(prev.speakers):
            with cols[i % len(cols)]:
                ap = s.avatar_path
                if ap and Path(ap).exists():
                    st.image(ap, width=72)
                st.markdown(f"**{s.name}**")
                st.caption(s.tts_provider or "—")
    except Exception as e:
        st.warning(f"Could not preview speakers: {e}")

st.caption("Edit speakers and voices on the **Speakers** and **Voices** pages.")

with st.expander("LLM and pipeline overrides", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("Outline provider", LLM_PROVIDERS, key="gen_outline_prov")
        st.text_input("Outline model", key="gen_outline_model")
        st.text_area("Outline config (JSON)", key="gen_outline_cfg", height=100)
    with c2:
        st.selectbox("Transcript provider", LLM_PROVIDERS, key="gen_tr_prov")
        st.text_input("Transcript model", key="gen_tr_model")
        st.text_area("Transcript config (JSON)", key="gen_transcript_cfg", height=100)
    st.slider("Number of segments", 1, 20, key="gen_num_seg")
    st.text_input("Language (optional, e.g. en, pl)", key="gen_lang")


def _parse_cfg(key: str) -> dict[str, Any]:
    raw = (st.session_state.get(key) or "").strip()
    if not raw:
        return {}
    return cast(dict[str, Any], json.loads(raw))


if st.button("Run pipeline", type="primary"):
    if not content.strip():
        st.error("Content is required")
    elif not ep_val:
        st.error("Select an episode profile (speakers and LLM defaults come from it).")
    else:
        try:
            oc = _parse_cfg("gen_outline_cfg")
            tc = _parse_cfg("gen_transcript_cfg")
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON in config fields: {e}")
        else:
            lang = (st.session_state.gen_lang or "").strip() or None
            try:
                with st.status("Generating podcast…", expanded=True) as status:
                    status.update(
                        label="Running LangGraph: outline → transcript → audio → combine…",
                        state="running",
                    )
                    result = asyncio.run(
                        create_podcast(
                            content=content,
                            briefing=st.session_state.gen_briefing or None,
                            episode_name=episode_name,
                            output_dir=output_dir,
                            episode_profile=ep_val,
                            outline_provider=st.session_state.gen_outline_prov,
                            outline_model=st.session_state.gen_outline_model,
                            transcript_provider=st.session_state.gen_tr_prov,
                            transcript_model=st.session_state.gen_tr_model,
                            num_segments=int(st.session_state.gen_num_seg),
                            outline_config=oc or None,
                            transcript_config=tc or None,
                            language=lang,
                        ),
                    )
                    status.update(label="Done", state="complete")
                st.success("Done")
                st.json({k: str(v) for k, v in result.items()})
                fp = result.get("final_output_file_path")
                if fp and Path(fp).exists():
                    st.audio(str(fp))
            except Exception as e:
                st.exception(e)
