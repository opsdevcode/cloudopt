"""OpenAI-compatible chat and embedding client (vLLM, OpenAI, etc.)."""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI, OpenAI

from packages.core.config import Settings, get_settings


def resolve_openai_compatible_settings(settings: Settings | None = None) -> tuple[str, str] | None:
    """
    Return (base_url, api_key) for an OpenAI-compatible HTTP API, or None if LLM is disabled.

    Precedence: CLOUDOPT_LLM_BASE_URL (+ CLOUDOPT_LLM_API_KEY / CLOUDOPT_OPENAI_API_KEY) >
    CLOUDOPT_OPENAI_API_KEY alone (OpenAI cloud).
    """
    s = settings or get_settings()
    if s.llm_base_url:
        key = s.llm_api_key or s.openai_api_key or "EMPTY"
        base = s.llm_base_url.rstrip("/")
        return base, key
    if s.openai_api_key:
        return "https://api.openai.com/v1", s.openai_api_key
    return None


class LLMClient:
    """Sync OpenAI-compatible client for workers and scripts."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        chat_model: str,
        embed_model: str,
        embedding_dimensions: int,
    ) -> None:
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._chat_model = chat_model
        self._embed_model = embed_model
        self.embedding_dimensions = embedding_dimensions

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> LLMClient | None:
        resolved = resolve_openai_compatible_settings(settings)
        if not resolved:
            return None
        base_url, api_key = resolved
        s = settings or get_settings()
        return cls(
            base_url=base_url,
            api_key=api_key,
            chat_model=s.llm_chat_model,
            embed_model=s.llm_embed_model,
            embedding_dimensions=s.embedding_dimensions,
        )

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Chat completion; parse assistant content as JSON object."""
        resp = self._client.chat.completions.create(
            model=self._chat_model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        if not content:
            return {}
        return json.loads(content)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors (dimension must match DB / settings)."""
        if not texts:
            return []
        resp = self._client.embeddings.create(model=self._embed_model, input=texts)
        return [list(d.embedding) for d in resp.data]


class AsyncLLMClient:
    """Async OpenAI-compatible client for FastAPI and asyncio workers."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        chat_model: str,
        embed_model: str,
        embedding_dimensions: int,
    ) -> None:
        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self._chat_model = chat_model
        self._embed_model = embed_model
        self.embedding_dimensions = embedding_dimensions

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> AsyncLLMClient | None:
        resolved = resolve_openai_compatible_settings(settings)
        if not resolved:
            return None
        base_url, api_key = resolved
        s = settings or get_settings()
        return cls(
            base_url=base_url,
            api_key=api_key,
            chat_model=s.llm_chat_model,
            embed_model=s.llm_embed_model,
            embedding_dimensions=s.embedding_dimensions,
        )

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        resp = await self._client.chat.completions.create(
            model=self._chat_model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        if not content:
            return {}
        return json.loads(content)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        resp = await self._client.embeddings.create(model=self._embed_model, input=texts)
        return [list(d.embedding) for d in resp.data]
