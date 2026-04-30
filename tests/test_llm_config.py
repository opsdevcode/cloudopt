"""Tests for OpenAI-compatible LLM configuration resolution."""

from __future__ import annotations

import pytest

from packages.ai.llm_client import resolve_openai_compatible_settings
from packages.core.config import Settings


def test_resolve_prefers_llm_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDOPT_LLM_BASE_URL", "http://vllm:8000/v1")
    monkeypatch.setenv("CLOUDOPT_LLM_API_KEY", "secret")
    monkeypatch.delenv("CLOUDOPT_OPENAI_API_KEY", raising=False)
    s = Settings()
    resolved = resolve_openai_compatible_settings(s)
    assert resolved is not None
    base, key = resolved
    assert base == "http://vllm:8000/v1"
    assert key == "secret"


def test_resolve_openai_cloud_when_no_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLOUDOPT_LLM_BASE_URL", raising=False)
    monkeypatch.setenv("CLOUDOPT_OPENAI_API_KEY", "sk-test")
    s = Settings()
    resolved = resolve_openai_compatible_settings(s)
    assert resolved is not None
    base, key = resolved
    assert base == "https://api.openai.com/v1"
    assert key == "sk-test"


def test_resolve_none_without_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDOPT_DATABASE_URL", "postgresql+asyncpg://x:x@localhost/db")
    monkeypatch.setenv("CLOUDOPT_DATABASE_URL_SYNC", "postgresql://x:x@localhost/db")
    monkeypatch.setenv("CLOUDOPT_LLM_BASE_URL", "")
    monkeypatch.setenv("CLOUDOPT_OPENAI_API_KEY", "")
    s = Settings()
    assert resolve_openai_compatible_settings(s) is None
