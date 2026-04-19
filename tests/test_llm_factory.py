from __future__ import annotations

import pytest
from langchain_openai import ChatOpenAI

from app.llm.factory import get_chat_model
from app.settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_openrouter_uses_chat_openai_with_base_url(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.delenv("OPENROUTER_HTTP_REFERER", raising=False)
    monkeypatch.delenv("OPENROUTER_X_TITLE", raising=False)
    llm = get_chat_model("openrouter", "openai/gpt-4o-mini")
    assert isinstance(llm, ChatOpenAI)


def test_openrouter_requires_key(monkeypatch):
    # Override .env so the test is deterministic when OPENROUTER_API_KEY is set locally
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        get_chat_model("openrouter", "openai/gpt-4o-mini")
