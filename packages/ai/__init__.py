"""AI recommendation engine (OpenAI-compatible LLMs, RAG, agent orchestration)."""

from packages.ai.analyzer import generate_recommendations, validate_finops_llm_payload
from packages.ai.llm_client import AsyncLLMClient, LLMClient, resolve_openai_compatible_settings

__all__ = [
    "AsyncLLMClient",
    "LLMClient",
    "generate_recommendations",
    "resolve_openai_compatible_settings",
    "validate_finops_llm_payload",
]
