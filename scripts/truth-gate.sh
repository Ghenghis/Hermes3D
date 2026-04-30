#!/usr/bin/env bash
# Unified truth gate — one command, one verdict, one signed bundle.
#
# Combines every layer the kit gates on:
#   1. Layer A static — ruff format/check, forbidden-pattern scan
#   2. Layer B unit + conformance pytest
#   3. Layer B+ acceptance runner (48-cell desk-organizer)
#   4. Layer C integration pytest
#   5. Layer D Playwright E2E (advisory — exit non-zero does NOT fail the gate)
#   6. Layer F honesty: regenerate manifest + honesty_diff
#   7. build-bundle: produce signed zip with all logs, screenshots, envelopes
#
# Final exit code:
#   0  = every blocking layer green
#   1  = at least one blocking layer failed (Layer D advisory ignored)
#
# The signed bundle is the single artifact reviewers should look at.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

UTC="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="var/truth-gate/${UTC}"
mkdir -p "$RUN_DIR/logs"

# Resolve python (cross-platform)
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else echo "[FAIL] python not found"; exit 1
fi

# Pyproject directory varies pre/post restructure
PYP="$ROOT/03_implementation"
[ -f "$ROOT/pyproject.toml" ] && PYP="$ROOT"

red()   { printf "\033[31m%s\033[0m\n" "$*"; }
grn()   { printf "\033[32m%s\033[0m\n" "$*"; }
yel()   { printf "\033[33m%s\033[0m\n" "$*"; }
blu()   { printf "\033[36m%s\033[0m\n" "$*"; }
hr()    { printf '%s\n' "------------------------------------------------------------"; }

VERDICTS=()
record() { VERDICTS+=("$1"); }    # "PASS|FAIL|ADVISORY <name>"

run_step() {
  local name="$1"; shift
  local advisory="${1:-no}"; shift || true
  local logf="$RUN_DIR/logs/${name// /_}.log"
  hr; blu "[step] $name"
  if "$@" >"$logf" 2>&1; then
    grn "  PASS  ($logf)"
    record "PASS $name"
    return 0
  else
    if [ "$advisory" = "advisory" ]; then
      yel "  ADVISORY-FAIL  ($logf — does not fail the gate)"
      record "ADVISORY $name"
      return 0
    fi
    red "  FAIL  ($logf)"
    record "FAIL $name"
    return 1
  fi
}

OVERALL_OK=1

blu "===== Hermes3D Truth Gate ($UTC) ====="
blu "Run dir: $RUN_DIR"

# Layer A — static gates
if command -v ruff >/dev/null 2>&1; then
  run_step "ruff format --check"     no    ruff format --check 03_implementation/src 04_testing/pytest || OVERALL_OK=0
  run_step "ruff check"              no    ruff check 03_implementation/src 04_testing/pytest || OVERALL_OK=0
else
  yel "[skip] ruff not installed — install with pip install ruff==0.14.14"
fi
run_step "forbidden-pattern scan"  no    "$PY" scripts/scaffolding/forbidden_pattern_scan.py || OVERALL_OK=0

# Layer B — unit + conformance + acceptance
run_step "pytest unit"             no    "$PY" -m pytest 04_testing/pytest/unit --tb=short -q --maxfail=20 || OVERALL_OK=0
run_step "pytest conformance"      no    "$PY" -m pytest 04_testing/pytest/conformance --tb=short -q || OVERALL_OK=0
run_step "acceptance runner"       no    "$PY" 04_testing/acceptance/run_acceptance.py || OVERALL_OK=0

# Layer C — integration (skip cleanly if matplotlib etc unavailable)
run_step "pytest integration"      no    "$PY" -m pytest 04_testing/pytest/integration --tb=short -q --maxfail=10 || OVERALL_OK=0

# Layer D — Playwright UI E2E (advisory until upstream gradio_client fix)
if [ -f "$ROOT/scripts/run-e2e.sh" ]; then
  run_step "run-e2e.sh (Playwright)" advisory bash "$ROOT/scripts/run-e2e.sh"
else
  yel "[skip] scripts/run-e2e.sh not present"
fi

# Layer F — honesty gates
run_step "regenerate manifest"     no    "$PY" 00_overview/contract/_generate_manifest.py || OVERALL_OK=0
run_step "honesty diff"            no    "$PY" scripts/scaffolding/honesty_diff.py || OVERALL_OK=0

# Always-on: build the proof bundle (will include all the logs above).
hr; blu "[step] build proof bundle"
if HERMES3D_PROOF_KEY="${HERMES3D_PROOF_KEY:-hermes3d-default-proof-key-not-secret}" \
   bash "$ROOT/scripts/build-bundle.sh" --output "$RUN_DIR" >"$RUN_DIR/logs/build-bundle.log" 2>&1; then
  BUNDLE="$(ls -1 "$RUN_DIR"/*.zip 2>/dev/null | head -1)"
  if [ -n "$BUNDLE" ]; then
    grn "  PASS  bundle: $BUNDLE"
    record "PASS build-bundle"
  else
    red "  FAIL  no bundle produced"; record "FAIL build-bundle"; OVERALL_OK=0
  fi
else
  red "  FAIL  see $RUN_DIR/logs/build-bundle.log"
  record "FAIL build-bundle"
  OVERALL_OK=0
fi

# Verify the bundle round-trips
if [ -n "${BUNDLE:-}" ]; then
  hr; blu "[step] verify proof bundle"
  if "$PY" 05_truth_proof/conformance_runner.py --bundle "$BUNDLE" >"$RUN_DIR/logs/bundle-verify.log" 2>&1; then
    grn "  PASS  signature + cross-refs verified"; record "PASS bundle-verify"
  else
    red "  FAIL  see $RUN_DIR/logs/bundle-verify.log"; record "FAIL bundle-verify"; OVERALL_OK=0
  fi
fi

# ---- Summary -------------------------------------------------------------
hr; blu "===== Truth Gate Summary ====="
for v in "${VERDICTS[@]}"; do
  case "$v" in
    PASS*) grn "  ✓ ${v#PASS }";;
    ADVISORY*) yel "  ~ ${v#ADVISORY } (advisory)";;
    FAIL*) red "  ✗ ${v#FAIL }";;
  esac
done
{
  printf "timestamp_utc=%s\n" "$UTC"
  printf "verdict=%s\n" "$([ $OVERALL_OK -eq 1 ] && echo GREEN || echo RED)"
  for v in "${VERDICTS[@]}"; do printf "step=%s\n" "$v"; done
  [ -n "${BUNDLE:-}" ] && printf "bundle=%s\n" "$BUNDLE"
} > "$RUN_DIR/summary.txt"

hr
if [ $OVERALL_OK -eq 1 ]; then
  grn "TRUTH GATE: GREEN"
  grn "Bundle: ${BUNDLE:-not produced}"
  exit 0
else
  red "TRUTH GATE: RED"
  red "See logs in $RUN_DIR/logs/"
  exit 1
fi
