#!/usr/bin/env bash
# scripts/run-e2e.sh — boot FastAPI + Gradio, run Playwright suite, tear down.
#
# This is the canonical Layer D (UI E2E) entrypoint. Wired into:
#   - agents/qa.yaml                       (qa role's blocking gate)
#   - scripts/scaffolding/test.sh --e2e    (developer-facing wrapper)
#   - .github/workflows/ci.yml             (Layer D CI job)
#
# Behaviour:
#   1. Boots `uvicorn hermes3d.api.server:app` on :8765 (kit canonical)
#   2. Boots `python -m hermes3d.app.launcher` on :7860
#   3. Polls both health endpoints up to 30s; fails fast on bring-up errors
#   4. Runs `npm test` in 04_testing/playwright
#   5. Captures both server logs to var/e2e-runs/<utc>/ regardless of pass/fail
#   6. Tears down both processes cleanly on exit
#   7. Exits with the Playwright run's exit code

set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

UTC_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$REPO_ROOT/var/e2e-runs/$UTC_STAMP"
mkdir -p "$RUN_DIR"

API_PORT="${HERMES3D_API_PORT:-8765}"
UI_PORT="${HERMES3D_UI_PORT:-7860}"

# Bind both servers to 0.0.0.0 by default in this script. This is the
# canonical containerized-server pattern: GitHub Actions Linux runners
# fail gradio's is_localhost_accessible() check when binding to
# 127.0.0.1, which makes gradio fall back to share-mode and triggers
# the upstream gradio_client schema-bool TypeError. Binding to all
# interfaces sidesteps the check; loopback connections from Playwright
# (HERMES3D_UI_URL stays 127.0.0.1) still work because 0.0.0.0 listeners
# accept loopback traffic.
HOST_BIND="${HERMES3D_HOST:-0.0.0.0}"
export HERMES3D_HOST="$HOST_BIND"
export HERMES3D_API_HOST="${HERMES3D_API_HOST:-$HOST_BIND}"

export PYTHONPATH="$REPO_ROOT/03_implementation/src:${PYTHONPATH:-}"
export HERMES3D_PROOF_KEY="${HERMES3D_PROOF_KEY:-hermes3d-default-proof-key-not-secret}"
export HERMES3D_API_URL="http://127.0.0.1:${API_PORT}"
export HERMES3D_UI_URL="http://127.0.0.1:${UI_PORT}"

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[FAIL] python not found on PATH" >&2
    exit 2
fi

API_LOG="$RUN_DIR/api.log"
UI_LOG="$RUN_DIR/ui.log"
PW_LOG="$RUN_DIR/playwright.log"

declare -a PIDS=()
EXIT_CODE=0

cleanup() {
    echo "[run-e2e] tearing down..."
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    # Give them a moment, then SIGKILL if still alive.
    sleep 1
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
        fi
    done
    wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[run-e2e] artifacts -> $RUN_DIR"

echo "[run-e2e] starting FastAPI on $HERMES3D_API_HOST:$API_PORT ..."
$PY -m uvicorn hermes3d.api.server:app \
    --host "$HERMES3D_API_HOST" --port "$API_PORT" --log-level info \
    > "$API_LOG" 2>&1 &
PIDS+=("$!")

echo "[run-e2e] starting Gradio launcher on $HERMES3D_HOST:$UI_PORT ..."
HERMES3D_PORT="$UI_PORT" \
    $PY -m hermes3d.app.launcher \
    > "$UI_LOG" 2>&1 &
PIDS+=("$!")

# Poll both endpoints. Fail fast (max 30s) and dump logs on timeout.
poll_url() {
    local url="$1" label="$2" deadline=$(( $(date +%s) + 30 ))
    while [[ $(date +%s) -lt $deadline ]]; do
        if curl -sf -o /dev/null --max-time 2 "$url"; then
            echo "[run-e2e]   $label ready: $url"
            return 0
        fi
        sleep 0.5
    done
    echo "[FAIL] $label did not come up at $url within 30s"
    echo "----- $label log -----"
    tail -n 80 "$3" 2>/dev/null || true
    echo "----------------------"
    return 1
}

poll_url "http://127.0.0.1:${API_PORT}/health" "FastAPI" "$API_LOG" || { EXIT_CODE=1; exit $EXIT_CODE; }
# Gradio's root returns HTML; treat any 200 as ready.
poll_url "http://127.0.0.1:${UI_PORT}/" "Gradio" "$UI_LOG" || { EXIT_CODE=1; exit $EXIT_CODE; }

echo "[run-e2e] running Playwright suite..."
(
    cd "$REPO_ROOT/04_testing/playwright"
    npm test 2>&1 | tee "$PW_LOG"
    exit "${PIPESTATUS[0]}"
)
EXIT_CODE=$?

# Always copy report dirs to the run dir.
if [[ -d "$REPO_ROOT/04_testing/playwright/playwright-report" ]]; then
    cp -r "$REPO_ROOT/04_testing/playwright/playwright-report" "$RUN_DIR/" 2>/dev/null || true
fi
if [[ -d "$REPO_ROOT/04_testing/playwright/test-results" ]]; then
    cp -r "$REPO_ROOT/04_testing/playwright/test-results" "$RUN_DIR/" 2>/dev/null || true
fi

echo "[run-e2e] exit=$EXIT_CODE   artifacts in $RUN_DIR"
exit "$EXIT_CODE"
