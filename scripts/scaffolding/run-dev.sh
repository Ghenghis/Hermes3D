#!/usr/bin/env bash
# scripts/run-dev.sh — start the dev stack (Gradio UI + REST API + supervisor).
#
# Usage:
#   bash scripts/run-dev.sh                # start all three
#   bash scripts/run-dev.sh --ui-only      # only the Gradio UI
#   bash scripts/run-dev.sh --api-only     # only the REST API
#   bash scripts/run-dev.sh --no-supervisor

set -u

UI=1
API=1
SUPERVISOR=1
REMOTE=0  # remote-control bridge (Telegram/Discord) — opt-in

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ui-only) UI=1; API=0; SUPERVISOR=0; shift ;;
        --api-only) UI=0; API=1; SUPERVISOR=0; shift ;;
        --no-supervisor) SUPERVISOR=0; shift ;;
        --no-ui) UI=0; shift ;;
        --no-api) API=0; shift ;;
        --remote) REMOTE=1; shift ;;
        --help|-h)
            grep '^#' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *) echo "[FAIL] unknown arg: $1"; exit 1 ;;
    esac
done

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

export PYTHONPATH="$REPO_ROOT/03_implementation/src:${PYTHONPATH:-}"
export HERMES3D_PROOF_KEY="${HERMES3D_PROOF_KEY:-hermes3d-default-proof-key-not-secret}"

mkdir -p "$REPO_ROOT/var" "$REPO_ROOT/logs"

declare -a PIDS=()

cleanup() {
    echo
    echo "[run-dev] shutting down ..."
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    wait 2>/dev/null
}
trap cleanup EXIT INT TERM

if [[ "$API" -eq 1 ]]; then
    echo "[run-dev] starting REST API on :8765 ..."
    uvicorn hermes3d.api.server:app --host 127.0.0.1 --port 8765 --log-level info \
        > "$REPO_ROOT/logs/api.log" 2>&1 &
    PIDS+=("$!")
    sleep 1
fi

if [[ "$SUPERVISOR" -eq 1 ]]; then
    echo "[run-dev] starting supervisor daemon ..."
    python3 -m hermes3d.core.supervisor.daemon \
        > "$REPO_ROOT/logs/supervisor.log" 2>&1 &
    PIDS+=("$!")
fi

if [[ "$REMOTE" -eq 1 ]]; then
    if [[ -z "${HERMES3D_TELEGRAM_BOT_TOKEN:-}" && -z "${HERMES3D_DISCORD_CONTROL_WEBHOOK:-}" ]]; then
        echo "[WARN] --remote requested but neither HERMES3D_TELEGRAM_BOT_TOKEN nor HERMES3D_DISCORD_CONTROL_WEBHOOK is set; skipping."
    else
        echo "[run-dev] starting remote-control bridge ..."
        python3 -m hermes3d.core.integrations.remote_control \
            > "$REPO_ROOT/logs/remote_control.log" 2>&1 &
        PIDS+=("$!")
    fi
fi

if [[ "$UI" -eq 1 ]]; then
    echo "[run-dev] starting Gradio UI on :7860 ..."
    echo "[run-dev]   logs in $REPO_ROOT/logs/, press Ctrl+C to stop"
    python3 -m hermes3d.app.launcher
else
    echo "[run-dev] no UI requested; press Ctrl+C to stop background services."
    wait
fi
