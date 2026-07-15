"""OpenAI-compatible chat and embedding client (vLLM, OpenAI, etc.)."""

from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass
from typing import Any, Literal, Protocol, cast, runtime_checkable

from openai import AsyncOpenAI, OpenAI

from packages.core.config import Settings, get_settings


@dataclass(frozen=True)
class ToolCallSpec:
    """OpenAI-style tool invocation from one assistant turn."""

    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class ChatRoundResult:
    """One chat completion turn (optional tool calls)."""

    content: str | None
    tool_calls: tuple[ToolCallSpec, ...]
    finish_reason: str | None


@runtime_checkable
class SyncChatClient(Protocol):
    """Common sync surface for real and sandbox LLM clients (used by the router)."""

    embedding_dimensions: int

    def chat_json(
        self, messages: list[dict[str, str]], *, temperature: float = 0.2
    ) -> dict[str, Any]: ...

    def chat_round(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Literal["auto", "none"] | None = "auto",
        temperature: float = 0.2,
        response_format: dict[str, str] | None = None,
    ) -> ChatRoundResult: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class AsyncChatClient(Protocol):
    """Common async surface for real and sandbox LLM clients (used by the router)."""

    embedding_dimensions: int

    async def chat_json(
        self, messages: list[dict[str, str]], *, temperature: float = 0.2
    ) -> dict[str, Any]: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


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

    @classmethod
    def from_profile(
        cls,
        provider: Any,
        tier: Any,
        *,
        embedding_dimensions: int,
    ) -> LLMClient:
        """Build a client from a resolved ProviderProfile + ModelTier (see packages.ai.routing)."""
        return cls(
            base_url=(provider.base_url or "https://api.openai.com/v1"),
            api_key=(provider.api_key or "EMPTY"),
            chat_model=tier.model,
            embed_model=tier.model,
            embedding_dimensions=embedding_dimensions,
        )

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Chat completion; parse assistant content as JSON object."""
        resp = self._client.chat.completions.create(
            model=cast(Any, self._chat_model),
            messages=cast(Any, messages),
            temperature=temperature,
            response_format=cast(Any, {"type": "json_object"}),
        )
        content = resp.choices[0].message.content
        if not content:
            return {}
        return cast(dict[str, Any], json.loads(content))

    def chat_round(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Literal["auto", "none"] | None = "auto",
        temperature: float = 0.2,
        response_format: dict[str, str] | None = None,
    ) -> ChatRoundResult:
        """
        Single completion turn; may return tool calls for a ReAct-style loop.

        Pass ``tool_choice=\"none\"`` to force a plain-text (e.g. JSON) reply when tools
        are still listed for providers that require tool schemas in history.
        """
        kwargs: dict[str, Any] = {
            "model": cast(Any, self._chat_model),
            "messages": cast(Any, messages),
            "temperature": temperature,
        }
        if tools is not None:
            kwargs["tools"] = cast(Any, tools)
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice
        if response_format is not None:
            kwargs["response_format"] = cast(Any, response_format)
        resp = self._client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        finish = getattr(resp.choices[0], "finish_reason", None)
        raw_calls = getattr(msg, "tool_calls", None) or []
        specs: list[ToolCallSpec] = []
        for tc in raw_calls:
            fn = getattr(tc, "function", None)
            if fn is None:
                continue
            specs.append(
                ToolCallSpec(
                    id=str(getattr(tc, "id", "") or ""),
                    name=str(getattr(fn, "name", "") or ""),
                    arguments=str(getattr(fn, "arguments", None) or "{}"),
                )
            )
        return ChatRoundResult(
            content=msg.content,
            tool_calls=tuple(specs),
            finish_reason=str(finish) if finish is not None else None,
        )

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

    @classmethod
    def from_profile(
        cls,
        provider: Any,
        tier: Any,
        *,
        embedding_dimensions: int,
    ) -> AsyncLLMClient:
        """Build an async client from a resolved ProviderProfile + ModelTier."""
        return cls(
            base_url=(provider.base_url or "https://api.openai.com/v1"),
            api_key=(provider.api_key or "EMPTY"),
            chat_model=tier.model,
            embed_model=tier.model,
            embedding_dimensions=embedding_dimensions,
        )

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        resp = await self._client.chat.completions.create(
            model=cast(Any, self._chat_model),
            messages=cast(Any, messages),
            temperature=temperature,
            response_format=cast(Any, {"type": "json_object"}),
        )
        content = resp.choices[0].message.content
        if not content:
            return {}
        return cast(dict[str, Any], json.loads(content))

    async def chat_round(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Literal["auto", "none"] | None = "auto",
        temperature: float = 0.2,
        response_format: dict[str, str] | None = None,
    ) -> ChatRoundResult:
        kwargs: dict[str, Any] = {
            "model": cast(Any, self._chat_model),
            "messages": cast(Any, messages),
            "temperature": temperature,
        }
        if tools is not None:
            kwargs["tools"] = cast(Any, tools)
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice
        if response_format is not None:
            kwargs["response_format"] = cast(Any, response_format)
        resp = await self._client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        finish = getattr(resp.choices[0], "finish_reason", None)
        raw_calls = getattr(msg, "tool_calls", None) or []
        specs: list[ToolCallSpec] = []
        for tc in raw_calls:
            fn = getattr(tc, "function", None)
            if fn is None:
                continue
            specs.append(
                ToolCallSpec(
                    id=str(getattr(tc, "id", "") or ""),
                    name=str(getattr(fn, "name", "") or ""),
                    arguments=str(getattr(fn, "arguments", None) or "{}"),
                )
            )
        return ChatRoundResult(
            content=msg.content,
            tool_calls=tuple(specs),
            finish_reason=str(finish) if finish is not None else None,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        resp = await self._client.embeddings.create(model=self._embed_model, input=texts)
        return [list(d.embedding) for d in resp.data]


# --- Offline sandbox provider -------------------------------------------------

_SANDBOX_SUMMARY = (
    "Sandbox LLM (offline): no live model configured. Configure CLOUDOPT_LLM_* or a routing "
    "config to enable real inference. See docs/MODEL_GUIDANCE.md."
)


def _deterministic_embedding(text: str, dimensions: int) -> list[float]:
    """Deterministic, network-free embedding derived from a hash of the text.

    Not semantically meaningful; only stable and dimension-correct so RAG storage/retrieval
    code paths work offline in tests and local dev.
    """
    vec: list[float] = []
    counter = 0
    while len(vec) < dimensions:
        digest = hashlib.sha256(f"{text}:{counter}".encode()).digest()
        # 8 float32s per 32-byte digest, scaled to [-1, 1).
        for i in range(0, len(digest), 4):
            (raw,) = struct.unpack("<I", digest[i : i + 4])
            vec.append((raw / 0xFFFFFFFF) * 2.0 - 1.0)
            if len(vec) >= dimensions:
                break
        counter += 1
    return vec[:dimensions]


class SandboxLLMClient:
    """Deterministic, offline stand-in that satisfies the sync client surface."""

    def __init__(self, *, embedding_dimensions: int) -> None:
        self.embedding_dimensions = embedding_dimensions

    def chat_json(
        self, messages: list[dict[str, str]], *, temperature: float = 0.2
    ) -> dict[str, Any]:
        return {"summary": _SANDBOX_SUMMARY, "findings": []}

    def chat_round(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Literal["auto", "none"] | None = "auto",
        temperature: float = 0.2,
        response_format: dict[str, str] | None = None,
    ) -> ChatRoundResult:
        # No tool calls: the agent loop terminates immediately and parses this JSON.
        content = json.dumps({"summary": _SANDBOX_SUMMARY, "findings": []})
        return ChatRoundResult(content=content, tool_calls=(), finish_reason="stop")

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_deterministic_embedding(t, self.embedding_dimensions) for t in texts]


class AsyncSandboxLLMClient:
    """Async counterpart of SandboxLLMClient."""

    def __init__(self, *, embedding_dimensions: int) -> None:
        self.embedding_dimensions = embedding_dimensions

    async def chat_json(
        self, messages: list[dict[str, str]], *, temperature: float = 0.2
    ) -> dict[str, Any]:
        return {"summary": _SANDBOX_SUMMARY, "findings": []}

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [_deterministic_embedding(t, self.embedding_dimensions) for t in texts]


# --- Routers ------------------------------------------------------------------


class LLMRouter:
    """Resolves a sync client per task/tier from a RoutingConfig (offline sandbox by default)."""

    def __init__(self, config: Any, *, embedding_dimensions: int) -> None:
        self._config = config
        self._embedding_dimensions = embedding_dimensions
        self._cache: dict[str, SyncChatClient] = {}

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        *,
        scan_override: dict[str, Any] | None = None,
    ) -> LLMRouter:
        from packages.ai.routing import resolve_routing

        s = settings or get_settings()
        config = resolve_routing(s, scan_override=scan_override)
        return cls(config, embedding_dimensions=s.embedding_dimensions)

    def client_for(self, task: str) -> SyncChatClient:
        from packages.ai.routing import KIND_SANDBOX

        provider, tier = self._config.resolve(task)
        key = f"{provider.name}:{tier.model}"
        if key not in self._cache:
            if provider.kind == KIND_SANDBOX:
                self._cache[key] = SandboxLLMClient(embedding_dimensions=self._embedding_dimensions)
            else:
                self._cache[key] = LLMClient.from_profile(
                    provider, tier, embedding_dimensions=self._embedding_dimensions
                )
        return self._cache[key]


class AsyncLLMRouter:
    """Async counterpart of LLMRouter."""

    def __init__(self, config: Any, *, embedding_dimensions: int) -> None:
        self._config = config
        self._embedding_dimensions = embedding_dimensions
        self._cache: dict[str, AsyncChatClient] = {}

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        *,
        scan_override: dict[str, Any] | None = None,
    ) -> AsyncLLMRouter:
        from packages.ai.routing import resolve_routing

        s = settings or get_settings()
        config = resolve_routing(s, scan_override=scan_override)
        return cls(config, embedding_dimensions=s.embedding_dimensions)

    def client_for(self, task: str) -> AsyncChatClient:
        from packages.ai.routing import KIND_SANDBOX

        provider, tier = self._config.resolve(task)
        key = f"{provider.name}:{tier.model}"
        if key not in self._cache:
            if provider.kind == KIND_SANDBOX:
                self._cache[key] = AsyncSandboxLLMClient(
                    embedding_dimensions=self._embedding_dimensions
                )
            else:
                self._cache[key] = AsyncLLMClient.from_profile(
                    provider, tier, embedding_dimensions=self._embedding_dimensions
                )
        return self._cache[key]
