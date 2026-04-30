"""Offline evaluation: validate structured FinOps LLM payloads without calling a live model."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.ai.analyzer import validate_finops_llm_payload
from packages.ai.rag import format_rag_block

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "golden_finops.json"


def _cases() -> list[dict]:
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return list(data["cases"])


@pytest.mark.parametrize("case", _cases(), ids=lambda c: c["name"])
def test_golden_payloads_validate(case: dict) -> None:
    normalized = validate_finops_llm_payload(case["llm_output"])
    assert "findings" in normalized
    assert isinstance(normalized["findings"], list)
    for f in normalized["findings"]:
        assert f["title"]
        assert f["category"]
        if case["name"] == "minimal_valid":
            assert "EKS" in normalized["summary"] or any(
                "EKS" in (f.get("description") or "") for f in normalized["findings"]
            )


def test_validate_rejects_non_object() -> None:
    with pytest.raises(ValueError):
        validate_finops_llm_payload([])


def test_format_rag_block_empty() -> None:
    assert format_rag_block([]) == ""


def test_format_rag_block_nonempty() -> None:
    text = format_rag_block(["alpha", "beta"])
    assert "Prior context" in text
    assert "alpha" in text and "beta" in text
