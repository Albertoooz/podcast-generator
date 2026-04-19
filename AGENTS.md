# AGENTS.md — working on podcast-generator

## What this repo is

Python 3.11 app: **LangGraph** pipeline (`outline → transcript → TTS clips → combine`) with **LangChain** chat models, **pluggable TTS** (Voxtral local/cloud/MLX, ElevenLabs, OpenAI, optional XTTS), **Langfuse** callbacks, **Streamlit** UI + **Typer** CLI.

## Commands

```bash
uv sync --all-groups
uv run pytest -v
uv run ruff check app tests && uv run ruff format app tests
uv run mypy app
uv run podcast-generator --help
uv run podcast-generator init
uv run pre-commit install   # optional Git hooks (Ruff + file checks)
uv run streamlit run app/ui/streamlit_app.py
```

## Layout

- `app/graph/` — `workflow.py` (`create_podcast`, compiled graph), `state.py`, `nodes/`
- `app/llm/factory.py` — `get_chat_model(provider, model, **cfg)`
- `app/tts/` — `registry.py`, `voice_library.py`, `providers/`
- `prompts/` — Jinja templates (repo root after clone; `./prompts/` after `podcast-generator init` in a project dir)
- `configs/` — local `speakers_library.json`, `voices.json`, `episodes.json` (gitignored here; created by `init`, not shipped with demo data)
- `deploy/langfuse/` — Docker Compose for **local Langfuse** (`make langfuse-up`)
- `docs/` — architecture, workflow, [llm-providers.md](docs/llm-providers.md), TTS matrix, voice cloning, Langfuse, [langfuse-local.md](docs/langfuse-local.md), [ffmpeg.md](docs/ffmpeg.md), [voxtral-local-setup.md](docs/voxtral-local-setup.md)

## Conventions

- **Async** graph nodes; I/O-bound work uses `asyncio.to_thread` where libraries are sync (OpenAI speech, pydub).
- **Pydantic v2** for `Outline`, `Transcript`, `Speaker`, `EpisodeProfile`.
- **Structured output**: `llm.with_structured_output(Outline|Transcript)` — do not hand-roll JSON parsers for LLM outputs.
- **Config cascade**: `app/config_loader.py` — inline overrides → `./configs/*.json` → optional `app/resources/episodes.json` → embedded episode skeleton.
- **New TTS provider**: add class in `app/tts/providers/`, register in `app/tts/registry.py`, document in `docs/tts-providers.md`, add tests.
- **New graph node**: add async function `(state, config) -> dict` partial update; register in `app/graph/workflow.py`.

## Playbooks

### Add a TTS provider

1. Implement `async def synthesize(self, text, speaker, output_file) -> Path` on a class with `name: str`.
2. Register in `app/tts/registry.py`.
3. Reference provider id on each **library speaker** in `configs/speakers_library.json` (`tts_provider` / `voice_ref`) or in `configs/voices.json`.
4. Extend `docs/tts-providers.md` matrix.

### Edit prompts

1. Prefer editing `./prompts/*.jinja` after `podcast-generator init`.
2. Keep sections `<briefing>`, `<context>`, `<speakers>`; include `style_description` for voice-aware dialogue.
3. Run a short generation to validate.

### Observability

- Set `LANGFUSE_*` in `.env`. Default host is **local** Langfuse (`http://localhost:3000`); use Langfuse Cloud by setting `LANGFUSE_HOST=https://cloud.langfuse.com`. See [docs/langfuse-local.md](docs/langfuse-local.md).
- Traces attach to `graph.ainvoke` via `get_langfuse_callbacks()`.
