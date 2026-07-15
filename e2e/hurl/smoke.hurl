# Stack smoke: API readiness
GET http://127.0.0.1:8000/health/ready
HTTP 200
[Asserts]
jsonpath "$.status" == "ready"

# Create finops scan (real enqueue → RQ worker)
POST http://127.0.0.1:8000/api/v1/scans
Content-Type: application/json
{"scan_kind":"finops","tenant_id":"hurl-e2e"}
HTTP 200
[Captures]
scan_id: jsonpath "$.id"

# Poll scan until terminal state (retry up to ~90s)
GET http://127.0.0.1:8000/api/v1/scans/{{scan_id}}
[Options]
retry: 45
retry-interval: 2000ms
HTTP 200
[Asserts]
jsonpath "$.status" == "completed"

# Summary reflects completed finops scan (sandbox LLM may yield 0 findings)
GET http://127.0.0.1:8000/api/v1/scans/{{scan_id}}/summary
HTTP 200
[Asserts]
jsonpath "$.status" == "completed"
jsonpath "$.scan_kind" == "finops"

# k8s_audit with Polaris metadata
POST http://127.0.0.1:8000/api/v1/scans
Content-Type: application/json
{
  "scan_kind": "k8s_audit",
  "tenant_id": "hurl-k8s",
  "metadata": {
    "k8s_audit": {
      "polaris": {
        "Results": [{
          "Name": "priorityClassNotSet",
          "Severity": "warning",
          "Category": "Reliability",
          "Message": "Pod lacks priority class",
          "Namespace": "prod",
          "Kind": "Deployment"
        }]
      }
    }
  }
}
HTTP 200
[Captures]
k8s_scan_id: jsonpath "$.id"

GET http://127.0.0.1:8000/api/v1/scans/{{k8s_scan_id}}
[Options]
retry: 30
retry-interval: 2000ms
HTTP 200
[Asserts]
jsonpath "$.status" == "completed"

GET http://127.0.0.1:8000/api/v1/findings?scan_id={{k8s_scan_id}}
HTTP 200
[Asserts]
jsonpath "$[0].framework" == "polaris"
