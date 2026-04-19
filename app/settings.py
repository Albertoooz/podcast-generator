from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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
