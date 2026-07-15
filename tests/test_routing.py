"""Offline tests for LLM routing resolution and the sandbox provider (no external services)."""

from __future__ import annotations

import json

import pytest

from packages.ai.llm_client import (
    AsyncSandboxLLMClient,
    LLMRouter,
    SandboxLLMClient,
)
from packages.ai.routing import (
    KIND_OPENAI_COMPATIBLE,
    KIND_SANDBOX,
    TIERS,
    default_sandbox_config,
    resolve_routing,
)
from packages.core.config import Settings


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "llm_mode": "auto",
        "llm_base_url": None,
        "llm_api_key": None,
        "openai_api_key": None,
        "llm_routing_json": None,
        "llm_routing_file": None,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_default_is_sandbox_for_all_tiers() -> None:
    config = resolve_routing(_settings())
    for tier in TIERS:
        provider, model = config.resolve(tier if tier != "standard" else "finops_agent")
        assert provider.kind == KIND_SANDBOX


def test_sandbox_config_binds_every_tier() -> None:
    config = default_sandbox_config()
    assert set(config.tiers) == set(TIERS)


def test_shorthand_base_url_routes_all_tiers() -> None:
    config = resolve_routing(
        _settings(llm_base_url="http://localhost:11434/v1", llm_chat_model="llama3")
    )
    provider, tier = config.resolve("finops_agent")
    assert provider.kind == KIND_OPENAI_COMPATIBLE
    assert provider.base_url == "http://localhost:11434/v1"
    assert tier.model == "llama3"
    embed_provider, embed_tier = config.resolve("embed")
    assert embed_provider.kind == KIND_OPENAI_COMPATIBLE


def test_mode_sandbox_forces_offline_even_with_base_url() -> None:
    config = resolve_routing(
        _settings(llm_mode="sandbox", llm_base_url="http://localhost:11434/v1")
    )
    provider, _ = config.resolve("finops_agent")
    assert provider.kind == KIND_SANDBOX


def test_routing_json_parsed() -> None:
    routing = {
        "providers": {"local": {"name": "local", "base_url": "http://x/v1", "api_key": "EMPTY"}},
        "tiers": {
            "embed": {"provider": "local", "model": "embed-m"},
            "cheap": {"provider": "local", "model": "cheap-m"},
            "standard": {"provider": "local", "model": "std-m"},
            "heavy": {"provider": "local", "model": "heavy-m"},
        },
    }
    config = resolve_routing(_settings(llm_routing_json=json.dumps(routing)))
    _, tier = config.resolve("finops_finalize")
    assert tier.model == "heavy-m"


def test_scan_override_pins_model() -> None:
    override = {
        "tiers": {"standard": {"provider": "local", "model": "pinned"}},
        "providers": {"local": {"name": "local", "base_url": "http://y/v1"}},
    }
    config = resolve_routing(
        _settings(llm_base_url="http://localhost:11434/v1"), scan_override=override
    )
    provider, tier = config.resolve("finops_agent")
    assert tier.model == "pinned"
    assert provider.base_url == "http://y/v1"


def test_scan_override_mode_sandbox_wins() -> None:
    config = resolve_routing(
        _settings(llm_base_url="http://localhost:11434/v1"),
        scan_override={"mode": "sandbox"},
    )
    provider, _ = config.resolve("finops_agent")
    assert provider.kind == KIND_SANDBOX


def test_task_to_tier_mapping() -> None:
    config = default_sandbox_config()
    assert config.tier_for_task("embed") == "embed"
    assert config.tier_for_task("finops_agent") == "standard"
    assert config.tier_for_task("finops_finalize") == "heavy"
    assert config.tier_for_task("unknown-task") == "standard"


def test_sandbox_client_chat_json_schema() -> None:
    client = SandboxLLMClient(embedding_dimensions=8)
    out = client.chat_json([{"role": "user", "content": "hi"}])
    assert "summary" in out
    assert out["findings"] == []


def test_sandbox_client_chat_round_terminates_without_tools() -> None:
    client = SandboxLLMClient(embedding_dimensions=8)
    result = client.chat_round([{"role": "user", "content": "hi"}])
    assert result.tool_calls == ()
    assert result.finish_reason == "stop"
    assert result.content is not None
    parsed = json.loads(result.content)
    assert parsed["findings"] == []


def test_sandbox_embeddings_deterministic_and_dimensioned() -> None:
    client = SandboxLLMClient(embedding_dimensions=16)
    a = client.embed(["hello", "world"])
    b = client.embed(["hello", "world"])
    assert len(a) == 2
    assert all(len(v) == 16 for v in a)
    assert a == b  # deterministic
    assert a[0] != a[1]  # distinct inputs -> distinct vectors


@pytest.mark.asyncio
async def test_async_sandbox_embeddings() -> None:
    client = AsyncSandboxLLMClient(embedding_dimensions=4)
    vecs = await client.embed(["x"])
    assert len(vecs) == 1 and len(vecs[0]) == 4


def test_router_returns_sandbox_by_default() -> None:
    router = LLMRouter.from_settings(_settings())
    client = router.client_for("finops_agent")
    assert isinstance(client, SandboxLLMClient)


def test_router_caches_client_per_key() -> None:
    router = LLMRouter.from_settings(_settings())
    assert router.client_for("finops_agent") is router.client_for("finops_agent")
