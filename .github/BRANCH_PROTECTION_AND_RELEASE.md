# Protected main and release setup

This repo is designed to use a **protected `main` branch** and **conventional-commit–driven releases**, like the reference TalentLayer setup. Follow these steps once per repository (or org) so CI and releases behave correctly.

## 1. Protect the `main` branch

In GitHub: **Settings → Code and automation → Rules → Rulesets** (or **Settings → Branches** for classic rules).

### Option A: Branch ruleset (recommended)

1. Click **New ruleset** (or **Add rule** for classic).
2. **Target:** Branch name pattern `main` (or use "Include default branch").
3. Enable:
   - **Require a pull request before merging** (required).
   - **Require approvals:** at least 1 (or more if you prefer).
   - **Require status checks before merging:** add the checks that must pass:
     - `Ruff lint` (from `ci.yml`)
     - `Mypy type-check` (from `ci.yml`)
     - `Pytest` (from `ci.yml`)
     - `Version check` (from `version-check.yml`)
     - `pip-audit` (from `security.yml`)
     - `Gitleaks` (from `security.yml`)
   - **Require review from Code Owners** (optional but recommended; requires `CODEOWNERS` to list at least one owner).
   - **Do not allow bypassing the above settings** (or allow only for specific actors; see step 2).
4. **Bypass list:** Add the user (or bot account) that will push the release version-bump commit (the same user whose token you will store in `RELEASE_PAT`; see step 2). That actor needs "Allow specified actors to bypass required pull requests" (classic) or bypass permission in the ruleset so the Release workflow can push the new tag and `pyproject.toml` change.

### Option B: Classic branch protection

1. **Settings → Branches → Add branch protection rule** (or edit rule for `main`).
2. **Branch name pattern:** `main`.
3. Check:
   - **Require a pull request before merging** (required, set minimum approvals).
   - **Require status checks before merging** and add the same status check names as above.
   - **Require review from Code Owners** if you use CODEOWNERS.
   - **Do not allow force pushes** / **Do not allow deletions** as desired.
4. Under **Allow specified actors to bypass required pull requests**, add the same user you will use for `RELEASE_PAT` (see below) so the Release workflow can push.

## 2. Add `RELEASE_PAT` for the Release workflow

When `main` is protected, the default `GITHUB_TOKEN` cannot push the version-bump commit and tag. The Release workflow (`.github/workflows/release.yml`) uses a Personal Access Token when provided.

1. Create a **Personal Access Token** (classic or fine-grained) with:
   - **repo** scope (classic), or **Contents: read and write** and **Metadata: read** (fine-grained).
2. In the repo: **Settings → Secrets and variables → Actions**.
3. Add a repository secret named **`RELEASE_PAT`** with the token value.
4. Ensure the user who owns the token is in the **bypass list** for the `main` branch rule (step 1). That way the Release workflow can push the version bump and tag to `main`.

The workflow uses `secrets.RELEASE_PAT || secrets.GITHUB_TOKEN`, so it still runs without `RELEASE_PAT` (e.g. on first push before protection is enabled), but once protection is on, `RELEASE_PAT` is required for the release to succeed.

## 3. CODEOWNERS (optional)

To use **Require review from Code Owners**, ensure `.github/CODEOWNERS` lists at least one owner (e.g. `* @opsdevcode/owners`). Then enable "Require review from Code Owners" in the branch rule.

## 4. Required status checks (summary)

Ensure these workflow job names are selected as required status checks for `main`:

| Job name        | Workflow        |
|-----------------|-----------------|
| Ruff lint       | CI              |
| Mypy type-check | CI              |
| Pytest          | CI              |
| Version check   | Version check   |
| pip-audit       | Security        |
| Gitleaks        | Security        |

If a job is skipped (e.g. path filter didn’t match), GitHub may still show it as success; you can require only the jobs that always run or that you care about.

## 5. Result

- All changes to `main` go through a PR.
- CI, version check, and security checks must pass.
- Merges to `main` trigger the Release workflow, which computes the next version from conventional commits, updates `pyproject.toml`, tags the release, and creates a GitHub release.
- The Release workflow pushes using `RELEASE_PAT`, so it works even with branch protection enabled.
