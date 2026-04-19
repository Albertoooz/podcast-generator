"""Browse generated episodes under output/."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

st.header("Episode library")

out = Path.cwd() / "output"
if not out.exists():
    st.info("No output/ yet. Generate an episode first.")
else:
    for ep in sorted(out.iterdir()):
        if not ep.is_dir():
            continue
        audio = ep / "audio"
        mp3s = list(audio.glob("*.mp3")) if audio.is_dir() else []
        with st.expander(ep.name):
            if mp3s:
                st.audio(str(mp3s[0]))
            tr = ep / "transcript.json"
            if tr.exists():
                st.text(tr.read_text(encoding="utf-8")[:4000])
