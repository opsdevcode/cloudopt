# Testing CloudOpt locally

CloudOpt has two testing lanes. A fresh clone passes the offline lane with **no API keys, no GPU, no Postgres/Redis, and no network**, because the LLM layer defaults to an offline **sandbox** provider.

## Prerequisites

```bash
pip install -e ".[dev]"
```

## Lane 1 — offline unit (default)

Runs everything that does not need a database. The sandbox LLM returns deterministic,
schema-valid responses, so agent/RAG code paths execute without a live model.

```bash
make test
# or:
CLOUDOPT_LLM_MODE=sandbox pytest -m "not integration"
```

- `tests/conftest.py` sets `CLOUDOPT_LLM_MODE=sandbox` by default.
- Integration-marked tests are auto-skipped when Postgres is unreachable, so this stays green on a bare clone.

## Lane 2 — integration (Postgres-backed)

For DB/worker-backed tests. Start services and migrate first:

```bash
make up        # docker-compose up -d postgres redis
make migrate   # alembic upgrade head
make test-all  # full suite (integration tests included)
```

Mark DB-dependent tests with `@pytest.mark.integration` so they are skipped in the offline lane
and run only when a database is available.

Integration tests live in `tests/test_api_integration.py` (health readiness, scans, findings, metrics).
They mock Redis/RQ enqueue so Postgres alone is sufficient locally.

## Coverage

Coverage is measured over `apps/` and `packages/` with a **40% minimum** gate (`fail_under` in `pyproject.toml`).

```bash
make test-cov   # full suite + terminal report (needs Postgres for integration tests)
```

CI runs `pytest --cov=apps --cov=packages` with Postgres up and migrations applied, so the **full suite**
(including integration tests) runs in the Pytest job—not the offline `-m "not integration"` lane.

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
```
