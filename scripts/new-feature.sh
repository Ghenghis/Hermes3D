#!/usr/bin/env bash
# Create a new feat/<area>/<short-desc> branch from origin/develop.
# Validates naming per BRANCH_STRATEGY.md.
set -euo pipefail

usage() {
  cat >&2 <<EOF
Usage: $0 <area> <short-desc>
  <area>        lowercase ASCII/digits/hyphens, e.g. "api", "ui", "kit"
  <short-desc>  lowercase ASCII/digits/hyphens, max 40 chars, e.g. "parse-stl"

Example:
  $0 api parse-stl   # creates feat/api/parse-stl
EOF
  exit 2
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then usage; fi

area="${1:-}"
desc="${2:-}"

if [ -z "$area" ]; then
  read -rp "area> " area
fi
if [ -z "$desc" ]; then
  read -rp "short-desc> " desc
fi

validate() {
  local label="$1" val="$2"
  if [ -z "$val" ]; then echo "ERROR: $label cannot be empty." >&2; exit 1; fi
  if [ ${#val} -gt 40 ]; then echo "ERROR: $label exceeds 40 chars." >&2; exit 1; fi
  if ! [[ "$val" =~ ^[a-z0-9-]+$ ]]; then
    echo "ERROR: $label must match [a-z0-9-]+ (no spaces, no uppercase, no underscores)." >&2
    exit 1
  fi
}

validate "area" "$area"
validate "short-desc" "$desc"

branch="feat/${area}/${desc}"

echo "Fetching origin/develop..."
git fetch origin develop

if git show-ref --verify --quiet "refs/heads/${branch}"; then
  echo "ERROR: branch '${branch}' already exists locally." >&2
  exit 1
fi

git checkout -b "${branch}" origin/develop

cat <<EOF

OK: created ${branch} from origin/develop.

Next steps:
  1. Run 'bash scripts/install-hooks.sh' once to enable the pre-push hook
     (refuses pushes to main/master, runs fast tests).
  2. Commit your work, then 'git push -u origin ${branch}'.
  3. Open a PR targeting 'develop' (NOT main).

Rules: see 06_release/BRANCH_STRATEGY.md.
EOF
