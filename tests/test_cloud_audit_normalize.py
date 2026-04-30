"""Normalizer tests for AWS Security Hub, Config, Polaris, kube-bench."""

from packages.cloud_audit.collectors.config_rules import config_rule_to_normalized
from packages.cloud_audit.collectors.k8s_json import (
    kube_bench_json_to_findings,
    polaris_json_to_findings,
)
from packages.cloud_audit.collectors.security_hub import security_hub_record_to_normalized


def test_security_hub_maps_severity_and_compliance():
    raw = {
        "Id": "arn:aws:securityhub:us-east-1:123:finding/abc",
        "Title": "S3 bucket public read",
        "Description": "Bucket allows public access.",
        "Severity": {"Label": "HIGH"},
        "Compliance": {"Status": "FAILED"},
        "Remediation": {"Recommendation": {"Text": "Restrict ACL"}},
        "Types": ["Software and Credential Configuration/Vulnerability/CVE"],
        "Resources": [{"Type": "AwsS3Bucket", "Id": "my-bucket"}],
        "RecordState": "ACTIVE",
        "Workflow": {"Status": "NEW"},
    }
    n = security_hub_record_to_normalized(raw)
    assert n.framework == "aws_security_hub"
    assert n.severity == "high"
    assert n.audit_status == "failed"
    assert n.resource_type == "AwsS3Bucket"
    assert n.recommendation == "Restrict ACL"


def test_config_rule_non_compliant():
    rule = {
        "ConfigRuleName": "encrypted-volumes",
        "Compliance": {
            "ComplianceType": "NON_COMPLIANT",
            "ComplianceContributorCount": {"CappedCount": 3, "CapExceeded": False},
        },
    }
    n = config_rule_to_normalized(rule)
    assert n is not None
    assert n.framework == "aws_config_rule"
    assert n.audit_status == "fail"
    assert n.control_id == "encrypted-volumes"


def test_config_rule_skips_compliant():
    rule = {
        "ConfigRuleName": "encrypted-volumes",
        "Compliance": {"ComplianceType": "COMPLIANT"},
    }
    assert config_rule_to_normalized(rule) is None


def test_polaris_results():
    payload = {
        "Results": [
            {
                "Name": "priorityClassNotSet",
                "Severity": "warning",
                "Category": "Reliability",
                "Message": "Pod lacks priority class",
                "Namespace": "prod",
                "Kind": "Deployment",
            }
        ]
    }
    rows = polaris_json_to_findings(payload)
    assert len(rows) == 1
    assert rows[0].framework == "polaris"
    assert rows[0].severity == "medium"


def test_kube_bench_controls():
    payload = {
        "Controls": [
            {
                "id": "3.1",
                "node_type": "master",
                "tests": [
                    {"test_number": "3.1.1", "desc": "Ensure dangerous plugin disabled", "status": "FAIL"}
                ],
            }
        ]
    }
    rows = kube_bench_json_to_findings(payload)
    assert len(rows) == 1
    assert rows[0].framework == "cis_kubernetes_benchmark"
    assert rows[0].audit_status == "fail"
    assert rows[0].control_id == "3.1.1"


def test_kube_bench_skips_pass():
    payload = {
        "controls": [
            {
                "id": "1",
                "tests": [{"test_number": "1.1", "desc": "ok", "status": "PASS"}],
            }
        ]
    }
    assert kube_bench_json_to_findings(payload) == []
