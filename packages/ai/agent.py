"""Thin agent orchestration: RAG retrieval + one structured LLM call (Phase C foundation)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from packages.ai.analyzer import FINOPS_SYSTEM_PROMPT, validate_finops_llm_payload
from packages.ai.llm_client import LLMClient
from packages.ai.rag import format_rag_block, retrieve_context_sync


def run_finops_agent_sync(
    session: Session,
    tenant_id: str,
    context: dict[str, Any],
    *,
    rag_query: str | None = None,
    client: LLMClient | None = None,
) -> dict[str, Any]:
    """
    Retrieve tenant-scoped chunks, then ask the LLM for structured FinOps JSON.

    This is intentionally a single reasoning step (not a multi-hop ReAct loop) so it stays
    predictable for workers; extend with explicit tools later.
    """
    llm = client or LLMClient.from_settings()
    if not llm:
        return {
            "summary": "LLM not configured.",
            "findings": [],
        }

    rag_block = ""
    q = rag_query or context.get("rag_query") or str(context.get("cluster_name") or "cost optimization")
    chunks = retrieve_context_sync(session, tenant_id, str(q), client=llm)
    rag_block = format_rag_block(chunks)

    import json

    user_parts: list[str] = []
    if rag_block:
        user_parts.append(rag_block)
    user_parts.append("Context JSON:\n" + json.dumps(context, default=str, indent=2)[:120000])
    messages = [
        {"role": "system", "content": FINOPS_SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]
    raw = llm.chat_json(messages)
    return validate_finops_llm_payload(raw)
