# CloudOpt.dev

CloudOpt is an **AI-assisted cloud platform** for teams operating **AWS** and **Kubernetes**. Instead of juggling separate FinOps spreadsheets, Security Hub consoles, Config dashboards, and one-off Polaris or kube-bench reports, CloudOpt **collects, normalizes, and serves** cost, security, and operational signals through a **single findings model**, a **REST API**, a **CLI**, and a **web console**—with optional **retrieval-grounded AI** when you configure an LLM.

Platform engineers, SREs, security/compliance teams, and FinOps practitioners get one workflow: **create a scan**, let background workers pull AWS posture or ingest Kubernetes audit JSON (or run the FinOps agent), then **query, filter, and summarize** everything as findings—with severity, resource linkage, framework metadata, and estimated monthly savings where applicable.

### FinOps and cost optimization

CloudOpt’s **FinOps agent** analyzes scan context and produces structured cost findings: title, category, severity, resource type/id, narrative description, actionable recommendation, and **estimated monthly savings**. Recommendations are **grounded in tenant-scoped RAG**—embeddings of prior findings and scan summaries stored in **Postgres + pgvector**—so suggestions reference your organization’s history, not opaque model memory.

The agent runs a **bounded tool-calling loop** (query recent findings, inspect the current scan, fetch cost metadata stubs) before synthesizing JSON output. You can route models by tier (`embed`, `cheap`, `standard`, `heavy`) to local Ollama/vLLM or any OpenAI-compatible provider; a **zero-config offline sandbox** is the default so clones and CI pass without API keys or GPUs. Deeper AWS billing integration (CUR, Cost Explorer) is on the roadmap; today the agent and tools establish the pipeline and finding shape.

### Posture and compliance (AWS)

For **`aws_audit`** and **`combined`** scans, workers use **read-only IAM** to collect:

- **AWS Security Hub** — active findings normalized with severity, compliance/workflow status, resource linkage, and remediation text (`framework: aws_security_hub`).
- **AWS Config** — non-compliant managed rules with contributor counts (`framework: aws_config_rule`).

Both land in the same **`Finding`** table as FinOps output, tagged `finding_kind: security`, with **`control_id`**, **`audit_status`**, and vendor **`details`** preserved for traceability. Tunable limits cap Security Hub and Config volume per scan.

### Kubernetes best practices (CNCF-aligned)

**`k8s_audit`** scans ingest JSON from tools you already run:

- **Polaris** (Fairwinds) — misconfigurations and best-practice gaps → `framework: polaris`, `finding_kind: operational_excellence`.
- **kube-bench** (CIS Kubernetes Benchmark) — failed controls → `framework: cis_kubernetes_benchmark`, `finding_kind: security`.

Pass reports via scan **`metadata.k8s_audit`** or the CLI (`cloudopt audit k8s --polaris-json … --kube-bench-json …`). CloudOpt does not replace in-cluster scanners; it **normalizes their output** into the shared model so K8s posture sits beside AWS and cost findings.

### Unified findings API

Every signal—LLM cost advice, Security Hub items, Config rule failures, Polaris checks, CIS failures—maps to one schema:

| Concept | Examples |
|---------|----------|
| **`finding_kind`** | `cost`, `security`, `operational_excellence` |
| **`framework`** | `aws_security_hub`, `aws_config_rule`, `polaris`, `cis_kubernetes_benchmark` |
| **`severity`** | `low`, `medium`, `high` |
| **Resource linkage** | AWS resource type/id or K8s namespace/kind/name |
| **FinOps fields** | `estimated_savings_monthly`, category (`compute`, `storage`, `kubernetes`, …) |

List and filter via **`GET /api/v1/findings`** (`scan_id`, `scan_kind`, `finding_kind`, `framework` prefix). Per-scan rollups live at **`GET /api/v1/scans/{id}/summary`**; cross-scan dashboards at **`GET /api/v1/metrics/overview`**. Scans progress **`pending` → `running` → `completed`** (or `failed`) through **Redis + RQ** workers.

### Retrieval-augmented search and Q&A

After scans complete, workers **upsert embeddings** of FinOps findings and scan summaries (and optionally top audit findings) into **`rag_chunks`**, keyed by tenant and source. The API exposes **`GET /api/v1/rag/search`** (semantic retrieval with optional `source_type` / `scan_id` filters) and **`POST /api/v1/rag/ask`** (grounded answers citing retrieved chunks). The web UI includes a **`/rag`** page for interactive search and ask. Without an LLM configured, ask still returns retrieved context—useful for debugging and offline dev.

### Scan modes at a glance

| `scan_kind` | What runs |
|-------------|-----------|
| `finops` | LLM FinOps agent → cost findings + RAG indexing |
| `aws_audit` | Security Hub + Config → security findings |
| `k8s_audit` | Polaris / kube-bench JSON from metadata → posture findings |
| `combined` | AWS audit first, then FinOps on the same scan |

### Architecture (summary)

**FastAPI** enqueues jobs; **RQ workers** dispatch by `scan_kind`; **PostgreSQL 16 + pgvector** stores scans, findings, and RAG chunks; **Redis** backs the queue. **Next.js** powers the console (overview, scans, findings, RAG). **Typer CLI** triggers audits against the API. Multi-tenancy uses **`tenant_id`** on scans and RAG data (default `"default"`). Docker Compose brings up Postgres, Redis, migrations, API, worker, and web with sensible defaults.

Roadmap items (see [PROJECT_SPEC.md](PROJECT_SPEC.md)) include fuller CUR/Cost Explorer ingestion, additional AWS sources (Trusted Advisor, Inspector, Prowler), and optional remediation automation (e.g. Terraform PRs).

## Capabilities

Quick reference (see sections above for detail):

| Area | What CloudOpt does today |
|------|---------------------------|
| **FinOps** | LLM agent with RAG + tool loop → structured cost findings and savings estimates |
| **AWS posture** | Security Hub + Config (read-only IAM) → normalized security findings |
| **Kubernetes** | Polaris + kube-bench JSON ingest → operational and CIS-aligned findings |
| **RAG** | Tenant-scoped pgvector index; search + grounded Q&A API and `/rag` UI |
| **Delivery** | FastAPI, Postgres/pgvector, Redis/RQ worker, Typer CLI, Next.js console |

## Local development

### Prerequisites

- Python 3.11+
- Node.js 20.19+ (only for the web UI in `apps/web`; see `apps/web/.nvmrc`)
- Docker and Docker Compose (for Postgres + Redis)
- Optional: AWS credentials (Cost Explorer, Security Hub, Config, etc.), LLM API keys or self-hosted OpenAI-compatible URL

By default the LLM layer runs in an **offline sandbox** (no keys, no network, no GPU), so a fresh clone stands up and passes tests without any external services. See [docs/MODEL_GUIDANCE.md](docs/MODEL_GUIDANCE.md) to plug in local (Ollama) or hosted models.

### 1. Clone and install

```bash
git clone https://github.com/opsdevcode/cloudopt.git
cd cloudopt
cp .env.example .env
# Edit .env if needed
pip install -e ".[dev]"
```

### 2. Start dependencies (Postgres + Redis)

```bash
docker-compose up -d postgres redis
```

### 3. Run migrations

```bash
alembic upgrade head
```

### 4. Run the API

```bash
uvicorn apps.api.main:app --reload --port 8000
```

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

### 5. Run the worker

Background scans are queued with **Redis (RQ)**. Start a worker so `POST /api/v1/scans` jobs run:

```bash
python -m apps.worker.main
```

Use Docker Compose to run API + worker + dependencies together (recommended).

### 6. Use the CLI

**FinOps (placeholder/stub until wired to the API):**

```bash
cloudopt scan
cloudopt scan --cluster production
cloudopt scan --output json
```

**Audits (requires API + worker running):**

```bash
# AWS posture (Security Hub + Config); set CLOUDOPT_API_BASE_URL if not localhost
cloudopt audit aws

# Kubernetes: pass Polaris and/or kube-bench JSON from files
cloudopt audit k8s --polaris-json ./polaris.json
cloudopt audit k8s --kube-bench-json ./kube-bench.json
cloudopt audit k8s --polaris-json ./polaris.json --kube-bench-json ./kube-bench.json
```

See `.env.example` for `CLOUDOPT_API_BASE_URL`, audit limits, and AWS/LLM variables.

### 7. Web UI (optional)

```bash
cd apps/web
npm ci
npm run dev
```

- Web UI: http://localhost:3000 (proxies `/api` and `/health` to the API on port 8000)

### Full stack with Docker Compose

```bash
cp .env.example .env   # optional; compose has sane defaults without it
docker-compose up --build
```

Migrations run automatically via a one-shot `migrate` service before the API and worker start, so the schema is ready on first boot. Then open:

- Web UI: http://localhost:3000
- API docs: http://localhost:8000/docs

For CLI commands against Dockerized services from your host, point `CLOUDOPT_DATABASE_URL` / `CLOUDOPT_API_BASE_URL` at `localhost` as needed.

## LLM routing

CloudOpt is provider-agnostic and never hardcodes a model. Tasks route to one of four tiers — `embed`, `cheap`, `standard`, `heavy` — bound to providers via configuration:

- **Offline sandbox (default):** no keys, no network, no GPU. A fresh clone runs and tests green.
- **Single-provider shorthand:** set `CLOUDOPT_LLM_BASE_URL` (+ `CLOUDOPT_LLM_CHAT_MODEL` / `CLOUDOPT_LLM_EMBED_MODEL`) to route all tiers to one OpenAI-compatible endpoint (local Ollama/vLLM or a cloud provider).
- **Multi-provider routing:** set `CLOUDOPT_LLM_ROUTING_JSON` or `CLOUDOPT_LLM_ROUTING_FILE` to bind each tier independently.
- **Per-scan override:** `scan.metadata.llm` can pin a tier/model (or `{"mode":"sandbox"}`) for one run.

Precedence: per-scan → env/file routing → `CLOUDOPT_LLM_*` shorthand → sandbox. See [docs/MODEL_GUIDANCE.md](docs/MODEL_GUIDANCE.md) for evidence-backed model suggestions and the routing schema.

## Testing

Two lanes (details in [TESTING.md](TESTING.md)):

```bash
make test       # offline unit lane: no services/keys/network (sandbox LLM)
make test-all   # full suite incl. integration (needs `make up && make migrate`)
```

A bare clone passes `make test` because the LLM layer defaults to the offline sandbox and integration tests auto-skip when Postgres is unreachable.

## Scan kinds

Create scans with `POST /api/v1/scans` and body field **`scan_kind`**:

| `scan_kind` | Behavior |
|-------------|----------|
| `finops` | LLM FinOps agent → cost findings (when LLM configured). |
| `aws_audit` | Security Hub + Config summaries → audit findings. |
| `k8s_audit` | Ingest Polaris/kube-bench JSON from `metadata.k8s_audit`. |
| `combined` | AWS audit findings, then FinOps agent on the same scan. |

Optional **`metadata`** on the scan can carry `k8s_audit` payloads for Kubernetes ingestion (see CLI example above).

## Project layout

```
cloudopt/
  apps/
    api/          # FastAPI (health, scans, findings)
    worker/       # RQ worker (dispatch_scan by scan_kind)
    cli/          # Typer CLI (scan, audit)
    web/          # Next.js console (dashboards, scans, findings, RAG)
  packages/
    core/         # Config, DB, models, job queue helper
    aws/          # boto3 clients (Cost Explorer, EKS, EC2, Security Hub, Config, …)
    cloud_audit/  # Collectors + normalization for AWS/K8s audits
    ai/           # LLM, RAG, FinOps agent
    finops/       # FinOps domain types
  alembic/        # Migrations
  tests/
  docs/
  infra/
```

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| GET | `/health/ready` | Readiness |
| POST | `/api/v1/scans` | Create scan (`scan_kind`, optional `metadata`, `tenant_id`, `cluster_name`) |
| GET | `/api/v1/scans` | List scans |
| GET | `/api/v1/scans/{id}` | Get scan |
| GET | `/api/v1/scans/{id}/summary` | Finding counts by severity and `finding_kind` |
| GET | `/api/v1/metrics/overview` | Cross-scan totals, savings sum, severity/kind breakdowns |
| GET | `/api/v1/findings` | List findings (`scan_id`, `scan_kind`, `finding_kind`, `framework` prefix) |
| GET | `/api/v1/findings/{id}` | Get finding |
| GET | `/api/v1/rag/search` | Semantic search over indexed findings/summaries (`tenant_id`, `q`, filters) |
| POST | `/api/v1/rag/ask` | Grounded Q&A using retrieved chunks |

Findings include **`finding_kind`** (e.g. `cost`, `security`), **`framework`** (e.g. `aws_security_hub`, `cis_kubernetes_benchmark`), **`control_id`**, and **`audit_status`** where applicable.

## AWS IAM (audits)

Use least-privilege roles for the worker. Typical read actions include Security Hub **GetFindings** (and list/describe as required by your partition) and Config **DescribeComplianceByConfigRule**. Tune limits with `CLOUDOPT_AUDIT_SECURITY_HUB_MAX_FINDINGS` and `CLOUDOPT_AUDIT_CONFIG_MAX_RULES`.

## Environment variables

All settings use the **`CLOUDOPT_`** prefix. See [`.env.example`](.env.example) for the full list.

## Documentation

- [PROJECT_SPEC.md](PROJECT_SPEC.md) — product scope and roadmap  
- [docs/LLM_AND_ACCOUNT_CONTEXT.md](docs/LLM_AND_ACCOUNT_CONTEXT.md) — LLM, RAG, and tenant-scoped context  
- [docs/MODEL_GUIDANCE.md](docs/MODEL_GUIDANCE.md) — evidence-backed model suggestions + routing schema  
- [TESTING.md](TESTING.md) — offline unit and integration testing lanes  
- [SECURITY.md](SECURITY.md) — reporting vulnerabilities  

## Protected main and releases

This repo uses a **protected `main` branch** and **conventional-commit–driven releases**. Merges to `main` (when path filters match) run the release workflow: version is computed from [conventional commits](https://www.conventionalcommits.org/), then `pyproject.toml` is updated, a tag is created, and a GitHub release is published. Maintainers can also run **Actions → Release → Run workflow** to retry after setup.

On protected `main`, `GITHUB_TOKEN` cannot push the version-bump commit (GH013). **One-time solo-org setup:** add repository secret **`RELEASE_PAT`** (fine-grained or classic PAT with contents write) and put the token owner on the `main` ruleset **bypass** list (including Code Scanning push gates). No ongoing PAT “refresh” unless the token expires or is revoked.

**Details:** [.github/BRANCH_PROTECTION_AND_RELEASE.md](.github/BRANCH_PROTECTION_AND_RELEASE.md) — rulesets, required checks, troubleshooting, and when to graduate to a GitHub App for team workflows.

## License

CloudOpt is distributed under the [BSD 3-Clause License](LICENSE).
