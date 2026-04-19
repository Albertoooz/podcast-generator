# Podcast Generator

AI podcast pipeline: **LangGraph** + **LangChain**, optional **Langfuse** tracing, pluggable **TTS** (Voxtral local/cloud, ElevenLabs, OpenAI, optional XTTS), **Streamlit** UI and **Typer** CLI.

## Quick start

1. **Install** (Python 3.11, [uv](https://docs.astral.sh/uv/)):

   ```bash
   cd podcast-generator
   uv sync --all-groups
   cp .env.example .env   # add API keys for LLM / TTS you use
   ```

2. **Templates:** `uv run podcast-generator init` writes `./prompts/` and `./configs/` (`episodes.json`, `speakers_library.json`, `voices.json`). Those JSON files start empty except for a minimal **`diverse_panel`** episode skeleton in `episodes.json` (from the app default until you edit it).

3. **Configure** (Streamlit **Episodes** / **Speakers** / **Voices**, or edit JSON under `configs/`):

   - Each episode profile needs **`speakers`**: a list of 1–4 ids that exist in **`configs/speakers_library.json`**.
   - Speakers usually reference **`configs/voices.json`** via `voice_ref`, or set `tts_provider` / presets per speaker.

   The directories **`configs/`** and **`voices/`** (samples) are **gitignored** — they stay local and are not part of the repo.

4. **UI:** from repo root, either:

   ```bash
   make ui
   ```

   or:

   ```bash
   uv run streamlit run app/ui/streamlit_app.py
   ```

   (`make ui` sets `PYTHONPATH` to the project root.)

5. **CLI generate** requires an episode id (**`--profile` / `-p`**), e.g.:

   ```bash
   uv run podcast-generator list-profiles
   uv run podcast-generator generate -c "Your topic text..." -e my_show -p diverse_panel -o output/my_show
   ```

   Optional **`--briefing`** overrides the profile’s `default_briefing` for that run.

## Docs

- [Architecture](docs/architecture.md)
- [Workflow](docs/workflow.md)
- [TTS providers](docs/tts-providers.md)
- [LLM providers](docs/llm-providers.md) (incl. OpenRouter)
- [Voice cloning](docs/voice-cloning.md)
- [Langfuse (observability)](docs/observability.md)
- [Langfuse self-host (local)](docs/langfuse-local.md)
- [What is ffmpeg?](docs/ffmpeg.md)
- [Voxtral TTS local (HF + vLLM-Omni)](docs/voxtral-local-setup.md)
- [AGENTS.md](AGENTS.md) — contributor / Cursor agent notes
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to contribute

## Voice cloning

Register voices in **`configs/voices.json`** with `podcast-generator clone-voice` (see `--help` for `--provider` / `--voice-id`) or the **Voices** page; attach them to speakers in **`configs/speakers_library.json`**. Details: [docs/voice-cloning.md](docs/voice-cloning.md).

## Development

```bash
uv run pytest -v
uv run ruff format app tests
uv run ruff check app tests
```

**Pre-commit:** after `uv sync --all-groups`, run `uv run pre-commit install` to wire Git hooks (see [CONTRIBUTING.md](CONTRIBUTING.md)). **CI:** pushes and PRs to `main` / `master` run [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (Ruff + pytest on Ubuntu).

**ffmpeg** is a system tool for audio processing; pydub uses it when concatenating MP3 clips. See [docs/ffmpeg.md](docs/ffmpeg.md).

**Langfuse** defaults to a **local** instance (`LANGFUSE_HOST=http://localhost:3000`). Run the bundled stack: `make langfuse-up` (see [deploy/langfuse/README.md](deploy/langfuse/README.md)). Keys and app wiring: [docs/langfuse-local.md](docs/langfuse-local.md). For Langfuse Cloud, set `LANGFUSE_HOST=https://cloud.langfuse.com` and project keys in `.env`.

Local **Voxtral TTS** (GPU + Hugging Face token): [docs/voxtral-local-setup.md](docs/voxtral-local-setup.md) — `make voxtral-model-download`, `make voxtral-up` or `./scripts/run_voxtral_server.sh`. **Apple Silicon** has no CUDA for the stock vLLM stack; use cloud TTS, a remote GPU, or the **MLX** path in that doc. See also [docs/tts-providers.md](docs/tts-providers.md).

GPU **Voxtral** via Docker: `docker compose --profile gpu up` (compose file / image may need tuning for your machine).

## License

MIT — see [LICENSE](LICENSE).
