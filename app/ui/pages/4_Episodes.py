"""Episode profiles — form editor for configs/episodes.json."""

from __future__ import annotations

import asyncio
import copy
import importlib.util
import json
import os
import tempfile
from pathlib import Path
from typing import Any

_b = Path(__file__).resolve().parent.parent / "_bootstrap.py"
_s = importlib.util.spec_from_file_location("podcast_streamlit_bootstrap", _b)
if _s and _s.loader:
    _mod = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(_mod)

import streamlit as st  # noqa: E402

from app.config_loader import (  # noqa: E402
    list_library_speaker_ids,
    load_episode_config_file_dict,
    load_episode_profile,
)
from app.graph.workflow import create_podcast  # noqa: E402
from app.models.episode import EpisodeConfig, EpisodeProfile, merge_episode_form  # noqa: E402

LLM_PROVIDERS = ["openai", "anthropic", "mistral", "ollama", "openrouter"]


def _config_path() -> Path:
    return Path.cwd() / "configs" / "episodes.json"


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def _clear_ep_keys() -> None:
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith("epfld_"):
            del st.session_state[k]


_UNSET_TEMP = -1.0  # sentinel meaning "use model default"


def _ensure_ep_keys(
    sel: str,
    prof: dict[str, Any],
    lib_ids: list[str],
) -> None:
    spk = prof.get("speakers") or []
    if spk and all(s in lib_ids for s in spk):
        st.session_state.setdefault(f"epfld_{sel}_spk", spk)
    else:
        default_spk = lib_ids[:2] if len(lib_ids) >= 2 else lib_ids[:1]
        st.session_state.setdefault(f"epfld_{sel}_spk", default_spk)
    st.session_state.setdefault(f"epfld_{sel}_op", prof.get("outline_provider", "openai"))
    st.session_state.setdefault(f"epfld_{sel}_om", prof.get("outline_model", "gpt-4o-mini"))
    ot = prof.get("outline_temperature")
    st.session_state.setdefault(f"epfld_{sel}_ot", float(ot) if ot is not None else _UNSET_TEMP)
    st.session_state.setdefault(f"epfld_{sel}_tp", prof.get("transcript_provider", "openai"))
    st.session_state.setdefault(f"epfld_{sel}_tm", prof.get("transcript_model", "gpt-4o-mini"))
    tt = prof.get("transcript_temperature")
    st.session_state.setdefault(f"epfld_{sel}_tt", float(tt) if tt is not None else _UNSET_TEMP)
    st.session_state.setdefault(f"epfld_{sel}_brief", prof.get("default_briefing", ""))
    st.session_state.setdefault(f"epfld_{sel}_ns", int(prof.get("num_segments", 4)))
    # Duration: derive minutes from stored words_per_segment (130 wpm)
    wps = prof.get("words_per_segment")
    dur_min = round(wps / 130, 1) if wps else 0.0
    st.session_state.setdefault(f"epfld_{sel}_dur", dur_min)
    st.session_state.setdefault(f"epfld_{sel}_lang", prof.get("language") or "")
    # Strip temperature from stored outline/transcript_config (now handled as dedicated field)
    oc = dict(prof.get("outline_config") or {})
    oc.pop("temperature", None)
    tc = dict(prof.get("transcript_config") or {})
    tc.pop("temperature", None)
    st.session_state.setdefault(f"epfld_{sel}_oc", json.dumps(oc, indent=2) if oc else "")
    st.session_state.setdefault(f"epfld_{sel}_tc", json.dumps(tc, indent=2) if tc else "")


def _collect_episode(sel: str) -> dict[str, Any]:
    oc_raw = st.session_state.get(f"epfld_{sel}_oc", "")
    tc_raw = st.session_state.get(f"epfld_{sel}_tc", "")
    try:
        oc = json.loads(oc_raw) if oc_raw.strip() else {}
        tc = json.loads(tc_raw) if tc_raw.strip() else {}
    except json.JSONDecodeError as e:
        raise ValueError(f"Advanced params JSON error: {e}") from e
    lang = st.session_state.get(f"epfld_{sel}_lang", "").strip()

    ot_raw = float(st.session_state.get(f"epfld_{sel}_ot", _UNSET_TEMP))
    tt_raw = float(st.session_state.get(f"epfld_{sel}_tt", _UNSET_TEMP))

    dur = float(st.session_state.get(f"epfld_{sel}_dur", 0.0))
    words_per_segment = int(round(dur * 130)) if dur > 0 else None

    out: dict[str, Any] = {
        "outline_provider": st.session_state.get(f"epfld_{sel}_op", "openai"),
        "outline_model": st.session_state.get(f"epfld_{sel}_om", ""),
        "outline_temperature": ot_raw if ot_raw != _UNSET_TEMP else None,
        "transcript_provider": st.session_state.get(f"epfld_{sel}_tp", "openai"),
        "transcript_model": st.session_state.get(f"epfld_{sel}_tm", ""),
        "transcript_temperature": tt_raw if tt_raw != _UNSET_TEMP else None,
        "default_briefing": st.session_state.get(f"epfld_{sel}_brief", ""),
        "num_segments": int(st.session_state.get(f"epfld_{sel}_ns", 4)),
        "words_per_segment": words_per_segment,
        "outline_config": oc or None,
        "transcript_config": tc or None,
        "language": lang or None,
    }
    sp = st.session_state.get(f"epfld_{sel}_spk") or []
    if len(sp) < 1 or len(sp) > 4:
        raise ValueError("Select 1–4 speakers from the library")
    out["speakers"] = sp
    return out


st.header("Episode profiles")

if "ep_data" not in st.session_state:
    try:
        st.session_state.ep_data = load_episode_config_file_dict()
    except FileNotFoundError:
        st.session_state.ep_data = {"profiles": {}}

data = st.session_state.ep_data
names = sorted(data["profiles"].keys())
lib_ids = list_library_speaker_ids()

col_a, col_b, col_c = st.columns([2, 1, 1])
with col_a:
    if not names:
        st.warning("No episode profiles yet.")
        sel = None
    else:
        sel = st.selectbox("Episode profile", names, key="ep_sel_pick")
with col_b:
    new_id = st.text_input("New episode id", placeholder="my_show")
with col_c:
    if st.button("New profile") and new_id.strip():
        eid = new_id.strip()
        if eid in data["profiles"]:
            st.error("Id already exists")
        elif not lib_ids:
            st.error(
                "Add at least one speaker under **Speakers** before creating an episode profile.",
            )
        else:
            data["profiles"][eid] = {
                "outline_provider": "openai",
                "outline_model": "gpt-4o-mini",
                "transcript_provider": "openai",
                "transcript_model": "gpt-4o-mini",
                "default_briefing": "Describe the episode tone and goals.",
                "num_segments": 4,
                "speakers": [lib_ids[0]],
            }
            st.session_state.ep_data = data
            _clear_ep_keys()
            st.session_state.ep_sel_pick = eid
            st.rerun()

r1, r2, r3, r4 = st.columns(4)
with r1:
    if names and sel and st.button("Duplicate"):
        dup = new_id.strip() or f"{sel}_copy"
        if dup in data["profiles"]:
            st.error("Target id exists")
        else:
            data["profiles"][dup] = copy.deepcopy(data["profiles"][sel])
            st.session_state.ep_data = data
            _clear_ep_keys()
            st.session_state.ep_sel_pick = dup
            st.rerun()
with r2:
    if names and sel and st.button("Delete", type="secondary"):
        del data["profiles"][sel]
        st.session_state.ep_data = data
        _clear_ep_keys()
        st.rerun()
with r3:
    if st.button("Reload from disk"):
        try:
            st.session_state.ep_data = load_episode_config_file_dict()
        except FileNotFoundError:
            st.session_state.ep_data = {"profiles": {}}
        _clear_ep_keys()
        st.rerun()
with r4:
    if st.button("Save to disk", type="primary") and sel:
        try:
            built = _collect_episode(sel)
            EpisodeProfile.model_validate(built)
            data["profiles"][sel] = built
            st.session_state.ep_data = data
            cfg = EpisodeConfig(**st.session_state.ep_data)
            _atomic_write_json(_config_path(), cfg.model_dump())
        except Exception as e:
            st.error(f"Save failed: {e}")
        else:
            st.success("Saved configs/episodes.json")

if not names or not sel:
    st.stop()

_ensure_ep_keys(sel, data["profiles"][sel], lib_ids)

st.subheader("Speakers")
st.caption("Pick **1–4** speakers from your library (configure them under **Speakers**).")
if not lib_ids:
    st.warning("No speakers in library yet — go to **Speakers** to add them.")
else:
    st.multiselect("Speakers (1–4)", lib_ids, key=f"epfld_{sel}_spk")

st.subheader("LLM and briefing")
st.caption(
    "**Outline provider** generates the episode structure (topics & segments). "
    "**Transcript provider** writes the actual dialogue. "
    "You can use different models for each — e.g. a fast model for outline, "
    "a more capable one for transcript."
)
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Outline** — episode structure")
    st.selectbox(
        "Provider",
        LLM_PROVIDERS,
        key=f"epfld_{sel}_op",
        help="LLM provider used to generate the outline (list of topics/segments).",
    )
    st.text_input(
        "Model",
        key=f"epfld_{sel}_om",
        help="Model name, e.g. `gpt-4o-mini`, `claude-3-5-haiku-latest`, `mistral-small-latest`.",
    )
    ot_val = st.session_state.get(f"epfld_{sel}_ot", _UNSET_TEMP)
    st.slider(
        "Temperature",
        min_value=_UNSET_TEMP,
        max_value=2.0,
        step=0.05,
        key=f"epfld_{sel}_ot",
        help=(
            "Controls creativity. -1 = use model default. "
            "0 = deterministic, 1 = balanced, 2 = very creative."
        ),
        format="default" if ot_val == _UNSET_TEMP else "%.2f",
    )
    if st.session_state.get(f"epfld_{sel}_ot", _UNSET_TEMP) == _UNSET_TEMP:
        st.caption("Temperature: model default")
    with st.expander("Advanced LLM parameters (JSON)", expanded=False):
        st.caption('Extra kwargs for the LLM — e.g. `{"top_p": 0.9, "max_tokens": 2048}`')
        st.text_area(
            "Outline extra params",
            key=f"epfld_{sel}_oc",
            height=80,
            label_visibility="collapsed",
        )

with c2:
    st.markdown("**Transcript** — dialogue writing")
    st.selectbox(
        "Provider",
        LLM_PROVIDERS,
        key=f"epfld_{sel}_tp",
        help="LLM provider used to write the speaker dialogue for each segment.",
    )
    st.text_input(
        "Model",
        key=f"epfld_{sel}_tm",
        help="Model name, e.g. `gpt-4o`, `claude-3-5-sonnet-latest`, `openai/gpt-4o` (OpenRouter).",
    )
    tt_val = st.session_state.get(f"epfld_{sel}_tt", _UNSET_TEMP)
    st.slider(
        "Temperature",
        min_value=_UNSET_TEMP,
        max_value=2.0,
        step=0.05,
        key=f"epfld_{sel}_tt",
        help=(
            "Controls creativity. -1 = use model default. "
            "0 = deterministic, 1 = balanced, 2 = very creative."
        ),
        format="default" if tt_val == _UNSET_TEMP else "%.2f",
    )
    if st.session_state.get(f"epfld_{sel}_tt", _UNSET_TEMP) == _UNSET_TEMP:
        st.caption("Temperature: model default")
    with st.expander("Advanced LLM parameters (JSON)", expanded=False):
        st.caption('Extra kwargs for the LLM — e.g. `{"top_p": 0.9, "max_tokens": 4096}`')
        st.text_area(
            "Transcript extra params",
            key=f"epfld_{sel}_tc",
            height=80,
            label_visibility="collapsed",
        )

st.text_area(
    "Default briefing",
    key=f"epfld_{sel}_brief",
    height=160,
    help=(
        "Instructions for the LLM: tone, goals, audience, style. "
        "Used when no briefing is given at generation time."
    ),
)

st.subheader("Episode length")
st.caption(
    "**Segments** are chapters — the outline splits the topic into this many distinct sections, "
    "each covering a sub-topic. More segments = more breadth. "
    "**Duration per segment** controls how long each segment's dialogue should be."
)
col_ns, col_dur = st.columns(2)
with col_ns:
    st.slider(
        "Number of segments (chapters)",
        1,
        20,
        key=f"epfld_{sel}_ns",
        help="How many distinct topics/chapters to cover. 4 ≈ 15–20 min podcast at 3 min/segment.",
    )
with col_dur:
    dur_raw = st.slider(
        "Target duration per segment (minutes)",
        min_value=0.0,
        max_value=5.0,
        step=0.5,
        key=f"epfld_{sel}_dur",
        help="0 = automatic (LLM decides). Each minute ≈ 130 spoken words.",
    )
    if dur_raw > 0:
        approx_words = int(round(dur_raw * 130))
        ns = int(st.session_state.get(f"epfld_{sel}_ns", 4))
        approx_total = dur_raw * ns
        st.caption(
            f"≈ **{approx_words} words** per segment · "
            f"total podcast ≈ **{approx_total:.0f} min** ({ns} segments)"
        )
    else:
        st.caption("Duration: automatic (LLM decides based on segment size hints)")

st.text_input(
    "Language (optional)",
    key=f"epfld_{sel}_lang",
    help=(
        "Force output language, e.g. `Polish`, `English`, `German`. "
        "Leave blank to follow the content."
    ),
)

st.divider()
if st.button("Validate JSON preview"):
    try:
        st.json(_collect_episode(sel))
    except Exception as e:
        st.error(e)

if st.button("Test run (smoke: short pipeline)"):
    try:
        built = _collect_episode(sel)
        base_ep = load_episode_profile(sel)
        ep_live = merge_episode_form(base_ep, built)
        EpisodeProfile.model_validate(ep_live.model_dump())
    except Exception as e:
        st.error(f"Invalid profile: {e}")
    else:
        out_dir = Path("output") / "_ui_smoke_test"
        with st.spinner("Running smoke test…"):
            try:
                result = asyncio.run(
                    create_podcast(
                        content="Short test paragraph about podcasting tools.",
                        episode_name="ui_smoke_test",
                        output_dir=str(out_dir),
                        episode=ep_live,
                        briefing=None,
                    ),
                )
            except Exception as e:
                st.exception(e)
            else:
                st.success("Smoke test finished")
                st.json({k: str(v) for k, v in result.items()})
                fp = result.get("final_output_file_path")
                if fp and Path(fp).exists():
                    st.audio(str(fp))
