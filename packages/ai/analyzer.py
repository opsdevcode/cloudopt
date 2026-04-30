"""FinOps analysis helpers: structured LLM output with optional RAG context."""

from __future__ import annotations

from typing import Any

from packages.ai.llm_client import LLMClient

FINOPS_SYSTEM_PROMPT = """You are a FinOps assistant for AWS and Kubernetes cost optimization.
Respond with a single JSON object only (no markdown). Use this shape:
{
  "summary": "short overall summary",
  "findings": [
    {
      "title": "string",
      "category": "string (e.g. compute, storage, networking, kubernetes)",
      "severity": "low|medium|high",
      "estimated_savings_monthly": number,
      "description": "string",
      "recommendation": "string",
      "resource_type": "string or null",
      "resource_id": "string or null"
    }
  ]
}
If data is insufficient, return an empty findings array and explain in summary."""


def analyze_cost_spike(raw_data: dict[str, Any]) -> dict[str, Any]:
    """
    Detect and explain sudden increases in AWS spend (stub when LLM unavailable).
    """
    return {
        "detected": False,
        "explanation": None,
        "recommendations": [],
        "raw_hint": raw_data.get("note"),
    }


def analyze_kubernetes_costs(raw_data: dict[str, Any]) -> dict[str, Any]:
    """Analyze pod/node/Karpenter signals (stub structure for scaffolding)."""
    return {
        "pod_rightsizing": [],
        "node_utilization": {},
        "karpenter_recommendations": [],
        "raw_hint": raw_data.get("note"),
    }


def generate_recommendations(
    context: dict[str, Any],
    *,
    rag_context_block: str = "",
) -> dict[str, Any]:
    """
    AI-generated cost optimization recommendations as structured JSON.
    When LLM is not configured, returns an empty result with a note.
    """
    client = LLMClient.from_settings()
    if not client:
        return {
            "summary": "LLM not configured (set CLOUDOPT_LLM_BASE_URL or CLOUDOPT_OPENAI_API_KEY).",
            "findings": [],
        }
    user_parts: list[str] = []
    if rag_context_block:
        user_parts.append(rag_context_block)
    user_parts.append("Context JSON:\n" + _safe_json(context))
    messages = [
        {"role": "system", "content": FINOPS_SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]
    return client.chat_json(messages)


def _safe_json(obj: Any) -> str:
    import json

    return json.dumps(obj, default=str, indent=2)[:120000]


def validate_finops_llm_payload(data: Any) -> dict[str, Any]:
    """Normalize / validate LLM JSON into a dict with findings list (raises ValueError if invalid)."""
    if not isinstance(data, dict):
        raise ValueError("LLM output must be a JSON object")
    findings = data.get("findings")
    if findings is None:
        findings = []
    if not isinstance(findings, list):
        raise ValueError("findings must be a list")
    out_findings: list[dict[str, Any]] = []
    for item in findings:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        if not title:
            continue
        out_findings.append(
            {
                "title": str(title)[:512],
                "category": str(item.get("category") or "general")[:64],
                "severity": str(item.get("severity") or "medium")[:32],
                "estimated_savings_monthly": float(item.get("estimated_savings_monthly") or 0.0),
                "description": (item.get("description") or None),
                "recommendation": (item.get("recommendation") or None),
                "resource_type": (item.get("resource_type") or None),
                "resource_id": (item.get("resource_id") or None),
            }
        )
    summary = str(data.get("summary") or "")
    return {"summary": summary, "findings": out_findings}
