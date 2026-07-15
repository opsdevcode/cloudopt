# CloudOpt.dev

CloudOpt is an **AI-assisted cloud platform** for **AWS** and **Kubernetes**. It brings together **FinOps** (cost optimization), **posture and compliance** (AWS-native and CNCF-aligned checks), and a unified **findings API** so platform and SRE teams can treat cost, security signals, and recommendations in one place.

## Capabilities

| Area | What CloudOpt does today |
|------|---------------------------|
| **FinOps** | Scans produce cost-oriented findings via an LLM-backed agent (when configured); findings are stored and exposed over the API. |
| **AWS posture** | Workers can pull **Security Hub** findings and **AWS Config** rule compliance summaries (read-only IAM), normalized into the same finding model. |
| **Kubernetes** | **Polaris** and **kube-bench** JSON reports can be attached to a scan; results are normalized into findings. |
| **Delivery** | FastAPI + Postgres + Redis (RQ worker); CLI for audits; optional self-hosted LLM via OpenAI-compatible endpoints. |

## Local development

### Prerequisites

- Python 3.11+
- Node.js 20+ (only for the web UI in `apps/web`)
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
| GET | `/api/v1/findings` | List findings (`scan_id`, `scan_kind`, `finding_kind`, `framework` prefix) |
| GET | `/api/v1/findings/{id}` | Get finding |

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

This repo uses a **protected `main` branch** and **conventional-commit–driven releases**. Merges to `main` (when path filters match) run the release workflow: version is computed from [conventional commits](https://www.conventionalcommits.org/), then `pyproject.toml` is updated, a tag is created, and a GitHub release is published. Maintainers can also run **Actions → Release → Run workflow** after fixing secrets or rules.

If `main` is protected (require PR, status checks, and/or Code Scanning gates), the default `GITHUB_TOKEN` cannot push the version-bump commit (GH013 / protected ref). Add a repository secret **`RELEASE_PAT`** (PAT with `repo` / contents write from a user or bot on the ruleset **bypass** list—including any Code Scanning push restrictions). The workflow uses `RELEASE_PAT` when set, otherwise `GITHUB_TOKEN`.

**One-time setup:** See [.github/BRANCH_PROTECTION_AND_RELEASE.md](.github/BRANCH_PROTECTION_AND_RELEASE.md) for rulesets, required status checks (CI, Security, CodeQL), `RELEASE_PAT`, and troubleshooting.

## License

CloudOpt is distributed under the [BSD 3-Clause License](LICENSE).
