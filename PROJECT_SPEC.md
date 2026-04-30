# CloudOpt.dev

CloudOpt.dev is an **AI-assisted cloud platform** for teams operating **AWS** and **Kubernetes**. It combines **FinOps** (cost visibility and savings recommendations), **cloud posture** (AWS Security Hub, AWS Config, and room for more integrations), and **Kubernetes best-practice checks** (e.g. Polaris, kube-bench), normalized into a single **findings** model and API.

Longer term the platform can ingest billing data and infrastructure signals at scale, analyze them with AI where appropriate, and eventually automate fixes (e.g. Terraform pull requests).

**Target users:** platform engineers, DevOps/SRE teams, security/compliance engineers, and FinOps teams.

**Differentiators:** unified cost + posture findings; deep Kubernetes awareness (cost and configuration); retrieval-grounded AI so recommendations stay tied to stored evidence.

---

## MVP and current direction

Near-term goals include:

1. AWS cost signals and FinOps-style findings (LLM-assisted when configured)
2. AWS posture ingestion (Security Hub, Config rule compliance summaries)
3. Kubernetes audit ingestion (Polaris / CIS-oriented kube-bench JSON)
4. API and CLI access to scans and findings
5. Background processing via Redis/RQ workers

Example FinOps-style outcomes (illustrative):

- Reduce EKS node shape or pool → estimated savings  
- Remove unused storage or idle network resources  
- Improve utilization (e.g. spot, rightsizing)

Example posture outcomes:

- Prioritized Security Hub findings with resource linkage  
- Non-compliant Config rules surfaced as tracked findings  
- Polaris / kube-bench gaps grouped by severity and framework  

---

## Technology stack

**Backend:** Python 3.11+, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Redis (RQ), Docker  

**CLI:** Typer  

**AI:** OpenAI-compatible APIs (cloud or self-hosted vLLM, etc.)  

**Infrastructure signals (directional):**

- AWS Cost Explorer, CUR (cost usage reports)  
- EKS, EC2, CloudWatch  
- AWS Security Hub, AWS Config  
- Kubernetes: Polaris, kube-bench (JSON ingestion); optional in-cluster or kubeconfig-based runners  

---

## Architecture

Components:

1. **API server** — REST API, orchestration, enqueue scan jobs  
2. **Worker** — Consumes RQ jobs; routes by `scan_kind` (FinOps agent, AWS collectors, K8s JSON ingest, or combined)  
3. **CLI** — Trigger flows and print results against the API  

High-level flow:

```text
AWS / K8s inputs (APIs, reports)
        ↓
    Collectors & normalization
        ↓
    Postgres (scans, findings, optional RAG chunks)
        ↓
Findings API + CLI  (+ optional LLM enrichment)
```

---

## Features (initial and adjacent)

**Cost and usage**

- Cost spike analysis (directional)  
- Kubernetes cost angles: requests vs usage, node utilization, autoscaling/Karpenter-friendly themes  

**Waste and efficiency**

- Unattached volumes, idle load balancers, orphaned ENIs, unused snapshots (as data becomes available)  

**Posture and compliance**

- Security Hub findings (normalized)  
- Config rule non-compliance summaries  
- Polaris / kube-bench JSON → findings  

**Right-sizing (FinOps)**

- Instance / capacity recommendations with estimated savings where modeled  

---

## Repository structure

```text
cloudopt/
  apps/
    api/
    worker/
    cli/
  packages/
    core/
    aws/
    cloud_audit/
    ai/
    finops/
  docs/
  infra/
  tests/
```

---

## CLI

- `cloudopt scan` — FinOps-oriented entrypoint (evolving; may call API in full deployments)  
- `cloudopt audit aws` — AWS posture scan via API  
- `cloudopt audit k8s --polaris-json …` / `--kube-bench-json …` — Kubernetes audits via API  

---

## Future features

- **Trusted Advisor** and additional AWS sources (Inspector, IAM Access Analyzer, OSS scanners such as Prowler) behind the same normalization layer  
- **Terraform / PR automation** — generated diffs and GitHub pull requests for approved remediations  
- **Web UI** — dashboards by pillar, framework, and trend across scans  

---

## Product vision

CloudOpt should behave like a **capable cloud teammate**: surface cost and risk, explain context with evidence, recommend concrete changes, and optionally implement safe fixes—with clear tenant boundaries and auditability rather than opaque model memory alone.
