#!/usr/bin/env bash
# Apply the committed main branch ruleset snapshot to GitHub.
# Requires gh auth with admin access to opsdevcode/cloudopt.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RULESET_ID="${CLOUDOPT_MAIN_RULESET_ID:-15804552}"
REPO="${CLOUDOPT_GITHUB_REPO:-opsdevcode/cloudopt}"

gh api -X PUT "repos/${REPO}/rulesets/${RULESET_ID}" \
  --input "${ROOT}/.github/rulesets/main.json"

echo "Applied ruleset ${RULESET_ID} for ${REPO} from .github/rulesets/main.json"
