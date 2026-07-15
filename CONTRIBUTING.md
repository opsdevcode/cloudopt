# Contributing to CloudOpt

Thank you for contributing. This repo uses a **protected `main` branch** — all changes go through pull requests.

## Branch workflow

1. Branch from latest `main`: `git checkout main && git pull && git checkout -b feat/short-name`
2. Make changes on your branch (never commit directly to `main`)
3. Open a PR using the [pull request template](.github/PULL_REQUEST_TEMPLATE.md)
4. After merge: the **remote branch is deleted automatically** (repo setting). Locally:
   `git checkout main && git pull && git branch -d <your-branch>`

When merging via CLI, use `gh pr merge --delete-branch` for the same behavior.

See also [`.cursor/rules/branch-workflow.mdc`](.cursor/rules/branch-workflow.mdc).

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/) — they drive automated versioning:

- `feat:` — new feature (minor bump)
- `fix:` — bug fix (patch bump)
- `docs:`, `chore:`, `test:`, `ci:`, `refactor:` — patch bump by default

Example: `feat(api): add pagination to scans list endpoint`

The **Version check** workflow comments on PRs with the release version preview when commits are valid.

## Local setup

```bash
pip install -e ".[dev]"
pre-commit install   # optional but recommended
```

For the web UI:

```bash
cd apps/web && npm ci
```

## Testing lanes

| Command | When |
|---------|------|
| `make test` | Lane 1 — offline unit tests (default; no Postgres/Redis) |
| `make test-all` | Lanes 1–2 (e2e skipped unless `CLOUDOPT_E2E_LIVE_API` set) |
| `make test-e2e` | Lane 3 — Compose + Hurl stack smoke (see `scripts/e2e-stack-smoke.sh`) |
| `make stack` | Full backend via Docker (postgres, redis, api, worker) for manual/e2e |
| `make test-cov` | Full suite + coverage report |
| `make check` | ruff + mypy + offline tests (CI-equivalent lint/typecheck) |
| `cd apps/web && npm test` | Vitest component smoke tests |
| `cd apps/web && npm run test:e2e` | Lane 4 — Playwright browser e2e (needs API running) |

Details: [TESTING.md](TESTING.md)

## Pre-PR checklist

Before pushing or opening a PR, run from the repo root:

```bash
ruff check .
ruff format --check .
mypy apps packages
pytest -m "not integration"    # offline lane
pytest -m "not e2e"            # PR-equivalent when Postgres is up
```

When changing application code or dependencies:

```bash
pip-audit
bandit -r apps packages alembic -c pyproject.toml -ll
```

For web changes: `cd apps/web && npm ci && npm run lint && npm test && npm run build`

## Branch protection and releases

Required CI checks, `RELEASE_PAT` one-time setup, and ruleset bypass are documented in [`.github/BRANCH_PROTECTION_AND_RELEASE.md`](.github/BRANCH_PROTECTION_AND_RELEASE.md).

To apply the committed ruleset snapshot after editing it:

```bash
./scripts/apply-main-ruleset.sh
```

## Security

Report vulnerabilities privately — see [SECURITY.md](SECURITY.md).
