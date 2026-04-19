"""LangChain chat model factory for multiple providers."""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from app.settings import get_settings


def get_chat_model(provider: str, model: str, **config: Any) -> BaseChatModel:
    """Return a LangChain chat model for the given provider."""
    settings = get_settings()
    p = provider.lower().strip()

    if p == "openai":
        from langchain_openai import ChatOpenAI

        kwargs = {k: v for k, v in config.items() if v is not None}
        return ChatOpenAI(model=model, api_key=settings.openai_api_key, **kwargs)

    if p == "anthropic":
        from langchain_anthropic import ChatAnthropic

        kwargs = {k: v for k, v in config.items() if v is not None}
        return ChatAnthropic(model=model, api_key=settings.anthropic_api_key, **kwargs)

    if p in ("mistral", "mistralai"):
        from langchain_mistralai import ChatMistralAI

        kwargs = {k: v for k, v in config.items() if v is not None}
        return ChatMistralAI(model=model, api_key=settings.mistral_api_key, **kwargs)

    if p == "ollama":
        from langchain_ollama import ChatOllama

        base_url = config.pop("base_url", None) or settings.ollama_base_url
        kwargs = {k: v for k, v in config.items() if v is not None}
        return ChatOllama(model=model, base_url=base_url, **kwargs)

    if p in ("openrouter", "open_router"):
        from langchain_openai import ChatOpenAI

        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is not set for LLM provider openrouter")
        kwargs = {k: v for k, v in config.items() if v is not None}
        base_url = kwargs.pop("base_url", None) or settings.openrouter_base_url
        headers: dict[str, str] = {}
        if settings.openrouter_http_referer:
            headers["HTTP-Referer"] = settings.openrouter_http_referer
        if settings.openrouter_x_title:
            headers["X-Title"] = settings.openrouter_x_title
        if headers and "default_headers" not in kwargs:
            kwargs["default_headers"] = headers
        return ChatOpenAI(
            model=model,
            api_key=settings.openrouter_api_key,
            base_url=base_url,
            **kwargs,
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")
