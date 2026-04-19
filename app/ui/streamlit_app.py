"""Podcast Generator — Streamlit entry (multi-page app). Redirects to Generate."""

from __future__ import annotations

import importlib.util
from pathlib import Path

# Repo root is not on sys.path by default; load app/ui/_bootstrap.py before other imports.
_bootstrap = Path(__file__).resolve().parent / "_bootstrap.py"
_spec = importlib.util.spec_from_file_location("podcast_generator_ui_bootstrap", _bootstrap)
if _spec and _spec.loader:
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Podcast Generator", layout="wide")
try:
    st.switch_page("pages/1_Generate.py")
except Exception as exc:  # noqa: BLE001 — show fallback if switch_page fails
    st.title("Podcast Generator")
    st.warning(f"Could not redirect automatically: {exc}")
    st.markdown("Use the sidebar **Generate** page, or open it below.")
    try:
        st.page_link("pages/1_Generate.py", label="Open Generate", icon="🎙️")
    except Exception:  # noqa: BLE001
        st.markdown("[Open Generate](pages/1_Generate.py)")
