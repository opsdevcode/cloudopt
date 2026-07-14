# Protected main and release setup

This repo uses a **protected `main` branch** and **conventional-commit–driven releases**. Follow these steps once per repository (or org) so CI and releases behave correctly.

Related workflow: [`.github/workflows/release.yml`](workflows/release.yml) (includes an inline troubleshooting header for GH013).

## 1. Protect the `main` branch

In GitHub: **Settings → Code and automation → Rules → Rulesets** (or **Settings → Branches** for classic rules).

### Option A: Branch ruleset (recommended)

1. Click **New ruleset** (or **Add rule** for classic).
2. **Target:** Branch name pattern `main` (or use "Include default branch").
3. Enable:
   - **Require a pull request before merging** (required).
   - **Require approvals:** at least 1 (or more if you prefer).
   - **Require status checks before merging:** add the checks that must pass (see [§4](#4-required-status-checks-summary)).
   - **Require review from Code Owners** (optional but recommended; requires `CODEOWNERS` to list at least one owner).
   - Optional: **Require code scanning results** / similar Code Scanning gates if enabled for the repo.
   - **Do not allow bypassing the above settings** for normal contributors (or allow only specific actors; see bypass below).
4. **Bypass list:** Add the user (or bot/GitHub App) that will push the release version-bump commit (the same identity whose token you store in `RELEASE_PAT`; see step 2). That actor needs bypass permission so the Release workflow can push the version commit and tag to `main`. If a ruleset blocks pushes while **waiting for Code Scanning** (or other PR-only checks), include those restrictions in the bypass as well—`GITHUB_TOKEN` alone cannot skip them.

### Option B: Classic branch protection

1. **Settings → Branches → Add branch protection rule** (or edit rule for `main`).
2. **Branch name pattern:** `main`.
3. Check:
   - **Require a pull request before merging** (required, set minimum approvals).
   - **Require status checks before merging** and add the same status check names as in §4.
   - **Require review from Code Owners** if you use CODEOWNERS.
   - **Do not allow force pushes** / **Do not allow deletions** as desired.
4. Under **Allow specified actors to bypass required pull requests**, add the same user you will use for `RELEASE_PAT` (see below) so the Release workflow can push.

## 2. Add `RELEASE_PAT` for the Release workflow

When `main` is protected, the default `GITHUB_TOKEN` cannot push the version-bump commit and tag. The Release workflow uses a Personal Access Token when provided.

1. Create a **Personal Access Token** (classic or fine-grained) with:
   - **repo** scope (classic), or **Contents: read and write** and **Metadata: read** (fine-grained).
2. In the repo: **Settings → Secrets and variables → Actions**.
3. Add a repository secret named **`RELEASE_PAT`** with the token value.
4. Ensure the user (or bot) who owns the token is on the **bypass list** for the `main` ruleset/protection (step 1), including any Code Scanning / status-check gates that reject direct pushes.

The workflow uses `secrets.RELEASE_PAT || secrets.GITHUB_TOKEN`. Without `RELEASE_PAT`, releases may still run on an unprotected `main`, but once protection (or Code Scanning push gates) is on, `RELEASE_PAT` plus bypass is required.

### Troubleshooting GH013 / protected ref failures

If Release fails with messages such as **GH013**, **Cannot update this protected ref**, **Changes must be made through a pull request**, or **Waiting for Code Scanning results**:

1. Confirm `RELEASE_PAT` is set and belongs to an account on the ruleset **Bypass list**.
2. Confirm that account can bypass **require pull request**, **required status checks**, and any **code scanning** / PR-only rules that block automated pushes to `main`.
3. After fixing secrets/rules, re-run: **Actions → Release → Run workflow** (`workflow_dispatch`), or wait for the next qualifying push to `main`.

## 3. CODEOWNERS (optional)

To use **Require review from Code Owners**, ensure `.github/CODEOWNERS` lists at least one owner (e.g. `* @opsdevcode/owners`). Then enable "Require review from Code Owners" in the branch rule.

## 4. Required status checks (summary)

Ensure these workflow **job names** are selected as required status checks for `main` (names must match GitHub’s check list exactly):

| Job name | Workflow |
|----------|----------|
| Ruff lint | CI (`ci.yml`) |
| Mypy type-check | CI (`ci.yml`) |
| Pytest | CI (`ci.yml`) |
| Version check | Version check (`version-check.yml`) |
| pip-audit | Security (`security.yml`) |
| Bandit | Security (`security.yml`) |
| npm audit (apps/web) | Security (`security.yml`) |
| Gitleaks | Security (`security.yml`) |
| Analyze | CodeQL (`codeql.yml`) |

Optional / path-filtered:

| Job name | Workflow | Notes |
|----------|----------|--------|
| CLI tests | CI (CLI) (`ci-cli.yml`) | Runs when CLI-related paths change; require only if you want it always gating merges |

If a job is skipped (e.g. path filter didn’t match), GitHub may still report success; prefer requiring jobs that always run or that you care about for every PR.

## 5. Result

- All changes to `main` go through a PR.
- CI, version check, security, and CodeQL checks must pass when required.
- Merges to `main` (and matching path filters) trigger the Release workflow, which computes the next version from conventional commits, updates `pyproject.toml`, tags the release, and creates a GitHub release.
- Maintainers can also start Release via **workflow_dispatch** after fixing `RELEASE_PAT` / bypass.
- The Release workflow pushes using `RELEASE_PAT` when set, so it works with branch protection and Code Scanning push gates.
