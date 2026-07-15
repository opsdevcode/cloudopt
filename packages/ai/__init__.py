"""AI recommendation engine (OpenAI-compatible LLMs, RAG, agent orchestration)."""

from packages.ai.analyzer import generate_recommendations, validate_finops_llm_payload
from packages.ai.llm_client import (
    AsyncLLMClient,
    AsyncLLMRouter,
    AsyncSandboxLLMClient,
    LLMClient,
    LLMRouter,
    SandboxLLMClient,
    resolve_openai_compatible_settings,
)
from packages.ai.routing import RoutingConfig, resolve_routing

__all__ = [
    "AsyncLLMClient",
    "AsyncLLMRouter",
    "AsyncSandboxLLMClient",
    "LLMClient",
    "LLMRouter",
    "RoutingConfig",
    "SandboxLLMClient",
    "generate_recommendations",
    "resolve_openai_compatible_settings",
    "resolve_routing",
    "validate_finops_llm_payload",
]
