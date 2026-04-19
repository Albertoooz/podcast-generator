# Contributing

Thanks for helping improve podcast-generator. This document explains how we work and what to check before opening a pull request.

## Prerequisites

- Python **3.11**
- [**uv**](https://docs.astral.sh/uv/) for dependencies and virtualenvs
- [**ffmpeg**](docs/ffmpeg.md) on your PATH (needed for the final audio combine step via pydub)

## Setup

```bash
git clone <your-fork-url>
cd podcast-generator
uv sync --all-groups
cp .env.example .env
```

Put API keys and local service URLs (LLM, TTS, Langfuse) in `.env` as needed. See [docs/langfuse-local.md](docs/langfuse-local.md) if you use self-hosted Langfuse.

## Pre-commit (optional)

Install hooks once so Ruff and basic checks run on `git commit`:

```bash
uv run pre-commit install
```

Run on all files manually:

```bash
uv run pre-commit run --all-files
```

Config: [`.pre-commit-config.yaml`](.pre-commit-config.yaml). CI on GitHub runs the same Ruff + pytest steps without requiring pre-commit.

## Making changes

1. **Branch** from `main` with a short descriptive name, e.g. `fix/tts-timeout` or `feat/voice-preview`.
2. **Keep scope focused** — one logical change per PR when possible.
3. **Match existing style** — typing, async patterns, loguru, Pydantic models as in the rest of `app/`.
4. **Update docs** when behavior, env vars, or setup steps change (README, `docs/`, or `AGENTS.md`).

## Checks before you push

Run from the repo root:

```bash
uv run ruff format app tests
uv run ruff check app tests
uv run pytest -v
```

Fix any failures before opening a PR. Optional: `uv run mypy app` if you touch typing-heavy code (project may use relaxed mypy settings).

## Pull requests

- Describe **what** changed and **why** (problem → solution).
- Link related issues if any.
- If you add a TTS provider or graph node, follow the playbooks in [AGENTS.md](AGENTS.md).

## Code of conduct

Be respectful and constructive in issues and reviews. Assume good intent.

## License

By contributing, you agree that your contributions are licensed under the same terms as the project — see [LICENSE](LICENSE).
