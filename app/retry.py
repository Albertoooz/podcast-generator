"""Retry helpers for LLM and TTS calls."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, TypeVar

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.settings import get_settings

F = TypeVar("F", bound=Callable[..., Any])


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, (ValueError, TypeError, KeyboardInterrupt)):
        return False
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 429:
            return True
        return code >= 500
    return isinstance(
        exc,
        (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError, OSError, TimeoutError),
    )


def get_retry_config(configurable: dict[str, Any] | None) -> dict[str, Any]:
    cfg = configurable or {}
    settings = get_settings()
    return {
        "max_attempts": int(
            cfg.get("retry_max_attempts", settings.podcast_retry_max_attempts),
        ),
        "wait_multiplier": int(
            cfg.get("retry_wait_multiplier", settings.podcast_retry_wait_multiplier),
        ),
        "wait_max": int(cfg.get("retry_wait_max", settings.podcast_retry_wait_max)),
    }


def get_retry_config_from_env() -> dict[str, Any]:
    return {
        "max_attempts": int(os.getenv("PODCAST_RETRY_MAX_ATTEMPTS", "3")),
        "wait_multiplier": int(os.getenv("PODCAST_RETRY_WAIT_MULTIPLIER", "5")),
        "wait_max": int(os.getenv("PODCAST_RETRY_WAIT_MAX", "30")),
    }


def create_retry_decorator(**kwargs: Any) -> Callable[[F], F]:
    max_attempts = kwargs.get("max_attempts", 3)
    multiplier = kwargs.get("wait_multiplier", 5)
    wait_max = kwargs.get("wait_max", 30)

    def deco(fn: F) -> F:
        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=multiplier, max=wait_max),
            retry=retry_if_exception(_is_transient),
            reraise=True,
        )(fn)

    return deco
