# Testing CloudOpt locally

CloudOpt uses a **polyglot testing pyramid**: fast Python unit/integration on every PR, stack smoke via Compose + Hurl, and optional Playwright browser checks.

| Lane | Scope | Command |
|------|--------|---------|
| 1 — offline unit | Sandbox LLM, mocked boundaries | `make test` |
| 2 — API integration | In-process FastAPI + Postgres (enqueue mocked) | `make test-all` (needs DB) |
| 3 — stack e2e | Compose + Hurl (+ optional 1 Python smoke) | `make test-e2e` |
| 4 — browser e2e (optional) | Playwright against Next.js + live API | `cd apps/web && npm run test:e2e` |

## Prerequisites

```bash
pip install -e ".[dev]"
```

For stack e2e, install [Hurl](https://hurl.dev/) (`brew install hurl` on macOS). The smoke script falls back to curl if Hurl is missing.

## Lane 1 — offline unit (default)

Runs everything that does not need a database. The sandbox LLM returns deterministic,
schema-valid responses, so agent/RAG code paths execute without a live model.

```bash
make test
# or:
CLOUDOPT_LLM_MODE=sandbox pytest -m "not integration"
```

- `tests/conftest.py` sets `CLOUDOPT_LLM_MODE=sandbox` by default.
- Integration tests auto-skip when Postgres is unreachable.

## Lane 2 — integration (Postgres-backed)

For API tests against a real database. Start services and migrate first:

```bash
make up        # docker compose up -d postgres redis
make migrate   # alembic upgrade head
pytest -m "not e2e"   # PR-equivalent gate (no stack smoke)
make test-all  # full pytest except skipped e2e without CLOUDOPT_E2E_LIVE_API
```

Integration tests live in `tests/test_api_integration.py` (health readiness, scans, findings, metrics).
They **mock** `enqueue_dispatch_scan` so Postgres alone is sufficient.

In-process worker logic (e.g. mocked AWS collectors) lives in `tests/test_worker_integration.py`
under the `integration` marker — no RQ subprocess in pytest.

## Lane 3 — stack e2e (Compose + Hurl)

Proves the full path: API → Redis/RQ → worker → Postgres, plus k8s metadata ingestion.

```bash
make test-e2e
# or:
./scripts/e2e-stack-smoke.sh
```

This script:

1. Starts `postgres`, `redis`, `api`, and `worker` via Docker Compose
2. Runs migrations
3. Executes `e2e/hurl/smoke.hurl` (finops + k8s paths)
4. Optionally runs one thin Python smoke when `RUN_PY_E2E=1`

Manual stack for debugging:

```bash
make stack     # postgres, redis, migrate, api, worker
hurl --test e2e/hurl/smoke.hurl
```

CI: **CI (E2E stack)** workflow (`ci-e2e.yml`) on relevant path changes or manual dispatch.

## Lane 4 — browser e2e (optional)

Playwright smoke against the Next.js UI (requires API at `CLOUDOPT_API_ORIGIN`, default `http://127.0.0.1:8000`):

```bash
make stack                    # or: make dev in one terminal
cd apps/web && npm ci
npm run test:e2e
```

CI: **CI (Web E2E)** workflow (`ci-web-e2e.yml`) starts the Compose backend, then runs Playwright.

## Component smoke (Vitest)

```bash
cd apps/web && npm test
```

Runs in **CI (Web)** on every web PR (lint + Vitest + build).

## Coverage

Coverage is measured over `apps/` and `packages/` with a **40% minimum** gate (`fail_under` in `pyproject.toml`).

```bash
pytest -m "not e2e" --cov=apps --cov=packages --cov-report=term-missing
```

CI **Pytest** job runs `pytest -m "not e2e"` with Postgres only (no Redis/worker spawn).

Ratchet `fail_under` upward as coverage improves (e.g. +5% per quarter).

## Real inference (optional, still local)

To exercise a real model without any cloud calls, run a local OpenAI-compatible server
(e.g. [Ollama](https://ollama.com/)) and point CloudOpt at it:

```bash
ollama serve
export CLOUDOPT_LLM_BASE_URL=http://localhost:11434/v1
export CLOUDOPT_LLM_CHAT_MODEL=llama3.1
export CLOUDOPT_LLM_EMBED_MODEL=nomic-embed-text
export CLOUDOPT_EMBEDDING_DIMENSIONS=768   # must match the embed model + DB vector column
```

See [docs/MODEL_GUIDANCE.md](docs/MODEL_GUIDANCE.md) for model suggestions and the routing schema.

## Full CI-equivalent check

```bash
make check   # ruff check + ruff format --check + mypy + offline tests
pytest -m "not e2e"   # when Postgres is up
```
