# CloudOpt.dev

AI-powered FinOps platform for AWS and Kubernetes cost optimization.

## Local development

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for Postgres + Redis)
- (Optional) AWS credentials and OpenAI/Anthropic API keys for full features

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

### 5. Run the worker (optional)

In a second terminal:

```bash
python -m apps.worker.main
```

### 6. Use the CLI

```bash
cloudopt scan
cloudopt scan --cluster production
cloudopt scan --output json
```

### Full stack with Docker Compose

To run API + worker + Postgres + Redis together:

```bash
docker-compose up --build
```

Then open http://localhost:8000 and run `cloudopt scan` locally against the same DB by pointing `CLOUDOPT_DATABASE_URL` at `localhost:5432` if needed.

## Project layout

```
cloudopt/
  apps/
    api/          # FastAPI server (health, scans, findings)
    worker/       # RQ background worker
    cli/          # Typer CLI (cloudopt scan)
  packages/
    core/         # Config, DB, models
    aws/          # AWS client placeholders (Cost Explorer, EKS, EC2, etc.)
    ai/           # AI analysis placeholders
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
| POST | `/api/v1/scans` | Create scan |
| GET | `/api/v1/scans` | List scans |
| GET | `/api/v1/scans/{id}` | Get scan |
| GET | `/api/v1/findings` | List findings (optional `?scan_id=`) |
| GET | `/api/v1/findings/{id}` | Get finding |

## Environment variables

All settings are prefixed with `CLOUDOPT_` and can be set in `.env` or the environment. See `.env.example` for the full list.

## Protected main and releases

This repo is set up for a **protected `main` branch** and **conventional-commit–driven releases**. Merges to `main` run the release workflow: version is computed from [conventional commits](https://www.conventionalcommits.org/), then `pyproject.toml` is updated, a tag is created, and a GitHub release is published.

If `main` is protected (e.g. "Require a pull request"), the default `GITHUB_TOKEN` cannot push the version-bump commit. Add a repository secret **`RELEASE_PAT`** (a Personal Access Token with `repo` scope from a user who can bypass branch protection) and, in **Settings → Branches → main**, add that user under "Allow specified actors to bypass required pull requests". The workflow uses `RELEASE_PAT` when set, otherwise `GITHUB_TOKEN`.

**One-time setup:** See [.github/BRANCH_PROTECTION_AND_RELEASE.md](.github/BRANCH_PROTECTION_AND_RELEASE.md) for step-by-step branch protection, required status checks, and CODEOWNERS.

## License

MIT
