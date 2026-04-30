"""Collect non-compliant AWS Config managed rules (summary per rule)."""

from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError

from packages.aws.client import get_config_client
from packages.cloud_audit.types import NormalizedAuditFinding


def config_rule_to_normalized(rule: dict[str, Any]) -> NormalizedAuditFinding | None:
    """Map describe_compliance_by_config_rule entry to a finding."""
    name = rule.get("ConfigRuleName")
    if not name:
        return None
    comp = rule.get("Compliance") or {}
    ctype = comp.get("ComplianceType")
    if ctype != "NON_COMPLIANT":
        return None
    contributors = comp.get("ComplianceContributorCount")
    count_str = ""
    if isinstance(contributors, dict):
        cap = contributors.get("CapExceeded")
        cnt = contributors.get("CappedCount")
        if cnt is not None:
            count_str = f" ({cnt}+ resources)" if cap else f" ({cnt} resources)"

    title = f"Config rule non-compliant: {name}{count_str}"[:512]
    return NormalizedAuditFinding(
        title=title,
        category="compliance",
        finding_kind="security",
        framework="aws_config_rule",
        control_id=str(name)[:512],
        audit_status="fail",
        severity="medium",
        description=f"AWS Config reports NON_COMPLIANT for rule {name}.",
        recommendation="Review Config evaluation results and remediate failing resources.",
        resource_type="AWS::Config::ConfigRule",
        resource_id=str(name)[:255],
        details={
            "config_rule_name": name,
            "compliance": comp,
        },
    )


def collect_config_non_compliant_rules(
    *, max_rules: int = 200
) -> tuple[list[NormalizedAuditFinding], str | None]:
    """Paginate Config compliance summaries; returns (findings, error_message)."""
    out: list[NormalizedAuditFinding] = []
    try:
        client = get_config_client()
    except Exception as exc:  # noqa: BLE001
        return [], f"config client: {exc}"

    paginator = client.get_paginator("describe_compliance_by_config_rule")
    try:
        for page in paginator.paginate(PaginationConfig={"PageSize": 100}):
            for rule in page.get("ComplianceByConfigRules") or []:
                if not isinstance(rule, dict):
                    continue
                n = config_rule_to_normalized(rule)
                if n:
                    out.append(n)
                if len(out) >= max_rules:
                    return out, None
    except ClientError as exc:
        return [], f"config: {exc.response.get('Error', {}).get('Message', exc)}"

    return out, None
