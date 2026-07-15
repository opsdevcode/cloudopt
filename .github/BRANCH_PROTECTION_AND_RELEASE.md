# Protected main and release setup

This repo uses a **protected `main` branch** and **conventional-commit–driven releases**. For a **solo org** (one owner, no collaborators), the steps below are a **one-time setup**—not an ongoing “PAT refresh” treadmill. Set `RELEASE_PAT` once (or again only if the token expires or is revoked).

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

## 2. One-time `RELEASE_PAT` for the Release workflow (solo org)

When `main` is protected, the default `GITHUB_TOKEN` cannot push the version-bump commit and tag—that is a GitHub platform rule (GH013), not a CloudOpt bug. The Release workflow uses a Personal Access Token when provided.

**Do this once** (repeat only if the token expires or is revoked):

1. Create a **fine-grained PAT** (preferred) scoped to this repo only, or a classic PAT with **repo** scope:
   - Fine-grained: **Contents: read and write**, **Metadata: read**
   - Optional: set an expiration (e.g. 90 days) and add a calendar reminder—still not scheduled “rotation automation”
2. In the repo: **Settings → Secrets and variables → Actions** → add secret **`RELEASE_PAT`** with the token value.
3. Add the token owner (your GitHub user or a release bot) to the **`main` ruleset bypass list** (step 1), including Code Scanning / status-check gates that block direct pushes.

The workflow uses `secrets.RELEASE_PAT || secrets.GITHUB_TOKEN`. Without `RELEASE_PAT` on a protected `main`, Release will compute the next version but fail when pushing the version commit and tag.

### When you add collaborators (defer until then)

| Approach | Long-lived secret? | Push to `main`? | Notes |
|----------|-------------------|-----------------|-------|
| **GitHub App** (release bot) | App private key in secrets | Yes, with app on bypass list | Best for teams / resale |
| **Release PR** | None beyond `GITHUB_TOKEN` | No — version bump via PR merge | No ruleset bypass needed |
| **Tag-only release** | None | No — version only in tag/Release | Diverges from `version_toml` model |
| **Manual release** | None | Maintainer tags when ready | Disable auto push trigger |

For multi-tenant or team workflows, prefer a **GitHub App** on the bypass list instead of a personal PAT.

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
| Web build | CI (Web) (`ci-web.yml`) | Lint, Vitest, and build when `apps/web/**` changes |
| CLI tests | CI (CLI) (`ci-cli.yml`) | Runs when CLI-related paths change |

If a job is skipped (e.g. path filter didn’t match), GitHub may still report success; prefer requiring jobs that always run or that you care about for every PR.

## 5. Ruleset as code

The `main` branch ruleset snapshot lives in [`.github/rulesets/main.json`](../rulesets/main.json). After editing it in a PR, apply to GitHub:

```bash
chmod +x scripts/apply-main-ruleset.sh
./scripts/apply-main-ruleset.sh
```

Override `CLOUDOPT_MAIN_RULESET_ID` or `CLOUDOPT_GITHUB_REPO` if needed.

## 6. Result

- All changes to `main` go through a PR.
- CI, version check, security, and CodeQL checks must pass when required.
- Merges to `main` (and matching path filters) trigger the Release workflow, which computes the next version from conventional commits, updates `pyproject.toml`, tags the release, and creates a GitHub release.
- Maintainers can also start Release via **workflow_dispatch** after fixing `RELEASE_PAT` / bypass.
- The Release workflow pushes using `RELEASE_PAT` when set, so it works with branch protection and Code Scanning push gates.
