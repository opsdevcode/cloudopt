"""Phase C agent: JSON extraction and tool loop (mocked LLM)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from packages.ai.agent import _extract_json_object, _finalize_json_round, run_finops_agent_sync
from packages.ai.llm_client import ChatRoundResult, ToolCallSpec


def test_extract_json_object_plain() -> None:
    d = _extract_json_object('{"summary":"ok","findings":[]}')
    assert d == {"summary": "ok", "findings": []}


def test_extract_json_object_fenced() -> None:
    raw = '```json\n{"summary":"x","findings":[]}\n```'
    d = _extract_json_object(raw)
    assert d == {"summary": "x", "findings": []}


def test_extract_json_object_brace_slice() -> None:
    d = _extract_json_object('preamble {"summary":"y","findings":[]} trailing')
    assert d == {"summary": "y", "findings": []}


def test_run_finops_agent_tool_loop_then_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("packages.ai.agent.retrieve_context_sync", lambda *a, **k: [])
    monkeypatch.setattr("packages.ai.agent.format_rag_block", lambda _chunks: "")

    def stub_execute(
        _name: str,
        _args: dict,
        *,
        session,
        tenant_id: str,
        scan_id: str | None,
    ) -> str:
        del session, tenant_id, scan_id
        return '{"ok":true}'

    monkeypatch.setattr("packages.ai.agent.execute_finops_tool", stub_execute)

    settings = MagicMock()
    settings.agent_tools_enabled = True
    settings.agent_max_tool_rounds = 6
    monkeypatch.setattr("packages.ai.agent.get_settings", lambda: settings)

    llm = MagicMock()
    llm.chat_round.side_effect = [
        ChatRoundResult(
            content=None,
            tool_calls=(ToolCallSpec(id="call_1", name="get_scan_snapshot", arguments="{}"),),
            finish_reason="tool_calls",
        ),
        ChatRoundResult(
            content='{"summary":"After tools","findings":[]}',
            tool_calls=(),
            finish_reason="stop",
        ),
    ]

    session = MagicMock()
    out = run_finops_agent_sync(
        session,
        "tenant-a",
        {"scan_id": "scan-1", "cluster_name": "prod"},
        client=llm,
    )
    assert out["summary"] == "After tools"
    assert out["findings"] == []
    assert llm.chat_round.call_count == 2


def test_finalize_json_round_uses_forced_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = MagicMock()
    llm.chat_round.return_value = ChatRoundResult(
        content='{"summary":"Forced","findings":[]}',
        tool_calls=(),
        finish_reason="stop",
    )
    messages = [{"role": "user", "content": "hi"}]
    out = _finalize_json_round(llm, messages)
    assert out["summary"] == "Forced"
    llm.chat_round.assert_called_once()
    kwargs = llm.chat_round.call_args.kwargs
    assert kwargs.get("tool_choice") == "none"
    assert kwargs.get("response_format") == {"type": "json_object"}
