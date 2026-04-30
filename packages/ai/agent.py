"""FinOps agent: RAG + bounded tool-calling loop (Phase C), then structured JSON."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from packages.ai.analyzer import FINOPS_SYSTEM_PROMPT, validate_finops_llm_payload
from packages.ai.llm_client import ChatRoundResult, LLMClient
from packages.ai.rag import format_rag_block, retrieve_context_sync
from packages.ai.tools import FINOPS_TOOL_DEFINITIONS, execute_finops_tool
from packages.core.config import get_settings

FINOPS_AGENT_SYSTEM_PROMPT = """You are a FinOps assistant for AWS and Kubernetes cost optimization.

You may call tools to load tenant-scoped facts (recent findings, this scan, billing placeholders, spike helper). Call tools when they would improve recommendations; you may use multiple rounds.

When you are finished using tools, respond with a single JSON object only (no markdown code fences), using exactly this shape:
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

If data is insufficient, return an empty findings array and explain in summary. Do not repeat tool results verbatim; synthesize recommendations.
"""


def _extract_json_object(text: str | None) -> dict[str, Any] | None:
    if not text or not str(text).strip():
        return None
    s = str(text).strip()
    if s.startswith("```"):
        lines = s.split("\n")
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    try:
        data = json.loads(s)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(s[start : end + 1])
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _assistant_message_dict(result: ChatRoundResult) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": "assistant", "content": result.content}
    if result.tool_calls:
        msg["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": tc.arguments},
            }
            for tc in result.tool_calls
        ]
    return msg


def _run_finops_agent_single_shot(
    session: Session,
    tenant_id: str,
    context: dict[str, Any],
    *,
    rag_query: str | None,
    client: LLMClient,
) -> dict[str, Any]:
    q = (
        rag_query
        or context.get("rag_query")
        or str(context.get("cluster_name") or "cost optimization")
    )
    chunks = retrieve_context_sync(session, tenant_id, str(q), client=client)
    rag_block = format_rag_block(chunks)

    user_parts: list[str] = []
    if rag_block:
        user_parts.append(rag_block)
    user_parts.append("Context JSON:\n" + json.dumps(context, default=str, indent=2)[:120000])
    messages = [
        {"role": "system", "content": FINOPS_SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]
    raw = client.chat_json(messages)
    return validate_finops_llm_payload(raw)


def _finalize_json_round(
    llm: LLMClient,
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Force JSON output (tool_choice none + json_object) after tool rounds."""
    extended = [
        *messages,
        {
            "role": "user",
            "content": (
                "Stop using tools. Respond with only the final JSON object "
                "(summary + findings) matching the schema from the system message."
            ),
        },
    ]
    forced = llm.chat_round(
        extended,
        tools=FINOPS_TOOL_DEFINITIONS,
        tool_choice="none",
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    parsed = _extract_json_object(forced.content)
    if isinstance(parsed, dict):
        return validate_finops_llm_payload(parsed)
    raw = llm.chat_json(
        [
            {"role": "system", "content": FINOPS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Produce the FinOps JSON from this working session.\n\n"
                    + json.dumps(messages, default=str)[:80000]
                ),
            },
        ]
    )
    return validate_finops_llm_payload(raw)


def run_finops_agent_sync(
    session: Session,
    tenant_id: str,
    context: dict[str, Any],
    *,
    rag_query: str | None = None,
    client: LLMClient | None = None,
) -> dict[str, Any]:
    """
    RAG retrieval, then either a single structured LLM call or a short tool loop (Phase C).

    Tool loop is bounded by ``CLOUDOPT_AGENT_MAX_TOOL_ROUNDS``; disable via
    ``CLOUDOPT_AGENT_TOOLS_ENABLED=false``.
    """
    llm = client or LLMClient.from_settings()
    if not llm:
        return {
            "summary": "LLM not configured.",
            "findings": [],
        }

    settings = get_settings()
    if not settings.agent_tools_enabled:
        return _run_finops_agent_single_shot(
            session, tenant_id, context, rag_query=rag_query, client=llm
        )

    q = (
        rag_query
        or context.get("rag_query")
        or str(context.get("cluster_name") or "cost optimization")
    )
    chunks = retrieve_context_sync(session, tenant_id, str(q), client=llm)
    rag_block = format_rag_block(chunks)

    user_parts: list[str] = []
    if rag_block:
        user_parts.append(rag_block)
    user_parts.append("Context JSON:\n" + json.dumps(context, default=str, indent=2)[:120000])
    user_initial = "\n\n".join(user_parts)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": FINOPS_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": user_initial},
    ]

    scan_id = context.get("scan_id")
    scan_id_str = str(scan_id) if scan_id else None

    max_rounds = max(1, settings.agent_max_tool_rounds)
    for _ in range(max_rounds):
        result = llm.chat_round(
            messages,
            tools=FINOPS_TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.2,
        )
        if result.tool_calls:
            messages.append(_assistant_message_dict(result))
            for tc in result.tool_calls:
                try:
                    args = json.loads(tc.arguments) if tc.arguments else {}
                except json.JSONDecodeError:
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                payload = execute_finops_tool(
                    tc.name,
                    args,
                    session=session,
                    tenant_id=tenant_id,
                    scan_id=scan_id_str,
                )
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": payload})
            continue

        parsed = _extract_json_object(result.content)
        if isinstance(parsed, dict):
            return validate_finops_llm_payload(parsed)
        messages.append(
            {
                "role": "user",
                "content": (
                    "Your last message was not valid JSON for the schema. "
                    "Reply with only one JSON object (summary + findings)."
                ),
            }
        )

    return _finalize_json_round(llm, messages)
