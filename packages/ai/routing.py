"""Provider-agnostic LLM routing configuration and resolution.

CloudOpt does not hardcode or mandate a model. Providers, models, and per-role tiers
are pure configuration resolved in layers (highest precedence first):

    per-scan override  ->  (per-tenant: deferred)  ->  env/routing file  ->  offline sandbox

The offline ``sandbox`` provider is the zero-config default so a fresh clone runs and
tests with no API keys, no network, and no GPU.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from packages.core.config import Settings, get_settings

# Fixed set of routing tiers (roles). Config may bind each to any provider/model.
TIERS: tuple[str, ...] = ("embed", "cheap", "standard", "heavy")

# Default task -> tier mapping (overridable via RoutingConfig.task_overrides).
DEFAULT_TASK_TIERS: dict[str, str] = {
    "embed": "embed",
    "finops_agent": "standard",
    "finops_finalize": "heavy",
}
_FALLBACK_TIER = "standard"

SANDBOX_PROVIDER = "sandbox"
KIND_SANDBOX = "sandbox"
KIND_OPENAI_COMPATIBLE = "openai_compatible"


class ProviderProfile(BaseModel):
    """A named connection to a model provider (OpenAI-compatible endpoint or the sandbox)."""

    name: str
    kind: str = KIND_OPENAI_COMPATIBLE
    base_url: str | None = None
    api_key: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ModelTier(BaseModel):
    """Binds a tier (role) to a provider + model."""

    provider: str
    model: str
    temperature: float = 0.2


class RoutingConfig(BaseModel):
    """Full routing configuration: providers, per-tier bindings, and task overrides."""

    providers: dict[str, ProviderProfile]
    tiers: dict[str, ModelTier]
    task_overrides: dict[str, str] = Field(default_factory=dict)

    def tier_for_task(self, task: str) -> str:
        """Resolve a task name to a tier, honoring overrides then defaults."""
        if task in self.task_overrides:
            return self.task_overrides[task]
        if task in DEFAULT_TASK_TIERS:
            return DEFAULT_TASK_TIERS[task]
        if task in self.tiers:
            return task
        return _FALLBACK_TIER

    def resolve(self, task: str) -> tuple[ProviderProfile, ModelTier]:
        """Return the (provider, tier) pair that should serve a given task."""
        tier_name = self.tier_for_task(task)
        tier = self.tiers.get(tier_name) or self.tiers[_FALLBACK_TIER]
        provider = self.providers.get(tier.provider)
        if provider is None:
            # Fall back to sandbox rather than raising, so a misconfiguration degrades safely.
            provider = _sandbox_provider()
        return provider, tier


def _sandbox_provider() -> ProviderProfile:
    return ProviderProfile(name=SANDBOX_PROVIDER, kind=KIND_SANDBOX)


def default_sandbox_config() -> RoutingConfig:
    """Every tier bound to the offline sandbox provider (zero-config default)."""
    providers = {SANDBOX_PROVIDER: _sandbox_provider()}
    tiers = {tier: ModelTier(provider=SANDBOX_PROVIDER, model=f"sandbox-{tier}") for tier in TIERS}
    return RoutingConfig(providers=providers, tiers=tiers)


def _config_from_shorthand(settings: Settings) -> RoutingConfig | None:
    """Build a single-provider config from the CLOUDOPT_LLM_* / OPENAI shorthand env, if set."""
    base_url: str | None = None
    api_key: str | None = None
    if settings.llm_base_url:
        base_url = settings.llm_base_url.rstrip("/")
        api_key = settings.llm_api_key or settings.openai_api_key or "EMPTY"
    elif settings.openai_api_key:
        base_url = "https://api.openai.com/v1"
        api_key = settings.openai_api_key
    else:
        return None

    provider = ProviderProfile(
        name="default",
        kind=KIND_OPENAI_COMPATIBLE,
        base_url=base_url,
        api_key=api_key,
    )
    chat_model = settings.llm_chat_model
    embed_model = settings.llm_embed_model
    tiers = {
        "embed": ModelTier(provider="default", model=embed_model),
        "cheap": ModelTier(provider="default", model=chat_model),
        "standard": ModelTier(provider="default", model=chat_model),
        "heavy": ModelTier(provider="default", model=chat_model),
    }
    return RoutingConfig(providers={"default": provider}, tiers=tiers)


def _load_routing_from_settings(settings: Settings) -> RoutingConfig | None:
    """Parse routing config from inline JSON or a JSON file, if configured."""
    raw: str | None = None
    if settings.llm_routing_json:
        raw = settings.llm_routing_json
    elif settings.llm_routing_file:
        path = Path(settings.llm_routing_file).expanduser()
        raw = path.read_text(encoding="utf-8")
    if raw is None:
        return None
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("routing config must be a JSON object")
    return RoutingConfig.model_validate(data)


def _apply_override(config: RoutingConfig, override: dict[str, Any]) -> RoutingConfig:
    """Apply a per-scan override dict onto a resolved config (shallow, tier/provider merges)."""
    if override.get("mode") == "sandbox":
        return default_sandbox_config()

    data = config.model_dump()
    for name, prof in (override.get("providers") or {}).items():
        merged = {**data["providers"].get(name, {"name": name}), **prof, "name": name}
        data["providers"][name] = merged
    for tier_name, tier in (override.get("tiers") or {}).items():
        merged = {**data["tiers"].get(tier_name, {}), **tier}
        data["tiers"][tier_name] = merged
    for task, tier_name in (override.get("task_overrides") or {}).items():
        data["task_overrides"][task] = tier_name
    return RoutingConfig.model_validate(data)


def resolve_routing(
    settings: Settings | None = None,
    *,
    scan_override: dict[str, Any] | None = None,
    tenant_config: dict[str, Any] | None = None,
) -> RoutingConfig:
    """Resolve the effective routing configuration.

    Precedence (highest first): per-scan override, per-tenant config (deferred; the
    ``tenant_config`` parameter is a seam and is not yet applied), env/file config or
    CLOUDOPT_LLM_* shorthand, then the offline sandbox default.
    """
    settings = settings or get_settings()

    if settings.llm_mode == "sandbox":
        config = default_sandbox_config()
    else:
        config = (
            _load_routing_from_settings(settings)
            or _config_from_shorthand(settings)
            or default_sandbox_config()
        )

    # tenant_config seam (deferred, post-auth): intentionally not applied yet.
    _ = tenant_config

    if scan_override:
        config = _apply_override(config, scan_override)

    return config
