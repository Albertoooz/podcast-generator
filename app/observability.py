"""Langfuse callback handler for LangGraph / LangChain (Langfuse v4+)."""

from __future__ import annotations

from typing import Any

from app.settings import get_settings

_langfuse_client: Any = None


def _ensure_langfuse_client() -> bool:
    """Initialize (once) the global Langfuse client required by CallbackHandler in v4.

    In Langfuse ≥ 4.x ``CallbackHandler`` looks up a client registered under the given
    ``public_key``.  The client must be created explicitly with all three credentials;
    env-var fallbacks are not used for this registry lookup.
    """
    global _langfuse_client  # noqa: PLW0603
    if _langfuse_client is not None:
        return True

    settings = get_settings()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return False

    try:
        from langfuse import Langfuse
    except ImportError:
        return False

    _langfuse_client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )
    return True


def get_langfuse_callbacks(_metadata: dict[str, Any] | None = None) -> list[Any]:
    """Return a ``[CallbackHandler]`` list if Langfuse is configured, else ``[]``."""
    if not _ensure_langfuse_client():
        return []

    try:
        from langfuse.langchain import CallbackHandler
    except ImportError:
        return []

    settings = get_settings()
    return [CallbackHandler(public_key=settings.langfuse_public_key)]
