.PHONY: sync install test lint format ui run help voxtral-model-download voxtral-up langfuse-up langfuse-down langfuse-logs

help:
	@echo "sync   - uv sync"
	@echo "test   - pytest"
	@echo "lint   - ruff + mypy"
	@echo "format - ruff format"
	@echo "ui     - streamlit run app/ui/streamlit_app.py"
	@echo "voxtral-model-download - prefetch Voxtral TTS from HF (needs HF_TOKEN in .env)"
	@echo "voxtral-up - docker compose --profile gpu up voxtral"
	@echo "langfuse-up   - local Langfuse (deploy/langfuse/docker-compose.yml)"
	@echo "langfuse-down / langfuse-logs - stop / follow web logs"

sync:
	uv sync --all-groups

install: sync

test:
	uv run pytest -v

lint:
	uv run ruff check app tests
	uv run mypy app

format:
	uv run ruff format app tests

ui:
	PYTHONPATH=$(CURDIR) uv run streamlit run app/ui/streamlit_app.py

run:
	uv run podcast-generator --help

voxtral-model-download:
	uv sync --group dev
	bash -c 'set -a && [ -f .env ] && . ./.env; set +a; uv run python scripts/download_voxtral_model.py'

voxtral-up:
	docker compose --profile gpu up voxtral

langfuse-up:
	cd deploy/langfuse && docker compose up -d

langfuse-down:
	cd deploy/langfuse && docker compose down

langfuse-logs:
	cd deploy/langfuse && docker compose logs -f langfuse-web
