from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Pydantic's env_file=".env" is cwd-relative; Streamlit may start with a different cwd.
# Resolve repo root (parent of ``app/``) so keys from the project ``.env`` always load.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _REPO_ROOT / ".env"
if _ENV_FILE.is_file():
    # ``override=True``: if the shell/IDE exported an empty ``ELEVENLABS_API_KEY=``, a
    # non-empty value from ``.env`` must still win (``override=False`` would keep "").
    load_dotenv(_ENV_FILE, override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.is_file() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    mistral_api_key: str | None = None
    ollama_base_url: str = "http://127.0.0.1:11434"

    # OpenRouter — OpenAI-compatible API (https://openrouter.ai/docs)
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Optional; OpenRouter uses them for analytics / rankings on their dashboard
    openrouter_http_referer: str | None = None
    openrouter_x_title: str | None = None

    elevenlabs_api_key: str | None = None
    voxtral_local_url: str = "http://127.0.0.1:8000"
    # Third-party MLX port (e.g. github.com/lbj96347/Mistral-TTS-iOS) — Apple Silicon only
    voxtral_mlx_root: str | None = None
    voxtral_mlx_model_path: str | None = None
    # API root with /v1 (not the full …/audio/speech path — that is auto-appended).
    mistral_tts_base_url: str = "https://api.mistral.ai/v1"

    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    # Default: local self-hosted Langfuse; override for Langfuse Cloud, e.g. https://cloud.langfuse.com
    langfuse_host: str = "http://localhost:3000"

    tts_batch_size: int = 5
    podcast_retry_max_attempts: int = 3
    podcast_retry_wait_multiplier: int = 5
    podcast_retry_wait_max: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()


def refresh_settings_env() -> None:
    """Reload project ``.env`` and invalidate cached ``Settings`` (Streamlit / shell quirks)."""
    if _ENV_FILE.is_file():
        load_dotenv(_ENV_FILE, override=True)
    get_settings.cache_clear()
