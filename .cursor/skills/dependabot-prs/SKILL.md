---
name: dependabot-prs
description: >-
  Triage, fix, test, and merge Dependabot pull requests for CloudOpt (npm in
  apps/web, pip/GitHub Actions). Use when the user mentions Dependabot, dependency
  PRs, npm lockfile conflicts, npm audit CI failures, or asks to merge/clear bot PRs.
---

# Dependabot PR workflow (CloudOpt)

Automate Dependabot fixes end-to-end: resolve conflicts, regenerate lockfiles, verify, merge.

## When to use

- Open PRs from `dependabot/*` branches
- CI failing on `npm audit (apps/web)` because `npm ci` breaks (lockfile drift or conflict markers)
- User asks to merge all dependency PRs or keep Dependabot green

## Prerequisites

```bash
gh pr list --state open --author app/dependabot
git fetch origin main
```

Node for `apps/web` (match `apps/web/.nvmrc`):

```bash
export PATH="$(dirname "$(which node)"):$PATH"   # or nvm/asdf use per .nvmrc
cd apps/web && node --version && npm ci
```

## Workflow

Copy and track:

```
- [ ] 1. Inventory open Dependabot PRs (note failing checks)
- [ ] 2. Merge low-risk PRs first (Actions, pip-only)
- [ ] 3. Fix each apps/web PR (conflicts + lockfile + test)
- [ ] 4. Merge with admin only after verification passes
- [ ] 5. Confirm main CI (Security npm audit, CI Web build)
```

### Step 1 — Classify PRs

| Type | Path signal | Merge strategy |
|------|-------------|----------------|
| GitHub Actions | `.github/workflows/**` | Needs `workflow` OAuth scope or UI merge |
| Python / pip | `pyproject.toml` only | Rebase/merge main; run `pip-audit` locally |
| npm / web | `apps/web/package*.json` | **Always regenerate lockfile** (below) |

### Step 2 — Resolve `apps/web` npm PRs (required pattern)

Conflict markers on `main` mean a prior bad merge — fix immediately:

```bash
rg '^<<<<<<<' apps/web/package.json apps/web/package-lock.json   # must be empty
```

**Preferred fix** (clean lockfile, applies Dependabot intent):

```bash
git fetch origin main
gh pr checkout <PR_NUMBER>
git checkout origin/main -- apps/web/package.json apps/web/package-lock.json
cd apps/web
npm install <package>@<target-version> [--save-dev]   # from Dependabot title/body
npm ci
npm audit --audit-level=high
npm run lint
npm run build
cd ../..
git add apps/web/package.json apps/web/package-lock.json
git commit -m "chore(deps): merge main and apply <package>@<version>"
git push origin HEAD
```

Do **not** push a lockfile if `npm ci` or `npm run build` failed locally.

### Step 3 — Major / breaking bumps

Before merging, confirm the repo supports the major version:

| Package | CloudOpt note |
|---------|----------------|
| **tailwindcss 4** | Requires `@tailwindcss/postcss` + config migration; stay on 3.4.x until migrated |
| **eslint 10** | `eslint-config-next` 16 peers ESLint 9; use ESLint 9 + flat config in `eslint.config.mjs` |
| **typescript 6** | Run `npm run build`; defer if Next/types break |
| **next major** | Verify `eslint.config.mjs`, lint script (`eslint .` not `next lint`), Docker/CI node version |

If migration is out of scope, **close the Dependabot PR** with a comment and pin/ignore until ready.

### Step 4 — Merge

```bash
gh pr merge <PR> --squash --admin   # after checks pass or admin override for unrelated flakes
```

- Cannot self-approve own PRs on GitHub; `--admin` bypasses review when permitted.
- Workflow PRs fail without `gh auth refresh -h github.com -s workflow` — tell the user to complete device auth or merge in UI.

### Step 5 — Post-merge verification on `main`

```bash
git checkout main && git pull origin main
rg '^<<<<<<<' apps/web/    # must be empty
cd apps/web && npm ci && npm audit --audit-level=high && npm run lint && npm run build
cd ../.. && ruff check . && mypy apps packages && CLOUDOPT_LLM_MODE=sandbox pytest -m "not integration"
```

Watch **Security** (`npm audit (apps/web)`) and **CI (Web)** on the latest `main` push.

## CloudOpt-specific pitfalls (learned)

1. **Conflict markers committed** — breaks `npm ci` in Security workflow; always grep before push.
2. **`npm install` without Node on PATH** — asdf shims fail silently; put real Node bin dir first on `PATH`.
3. **Stacking many npm Dependabot merges** — causes lockfile conflicts; merge/rebase one at a time.
4. **Next.js 16** — removed `next lint`; use `"lint": "eslint ."` with native flat config from `eslint-config-next/core-web-vitals`.
5. **Release workflow** — separate from Dependabot; needs `RELEASE_PAT` + ruleset bypass (see `.github/BRANCH_PROTECTION_AND_RELEASE.md`).

## Output

Report: PRs merged, PRs skipped (with reason), commands run, and any remaining manual steps (workflow scope, RELEASE_PAT, major migrations).
