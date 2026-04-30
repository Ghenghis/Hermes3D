#!/usr/bin/env bash
# wizard-record.sh — proof-recording wrapper around scripts/wizard.sh.
#
# Captures the entire interactive session (banners, command output, exit
# codes, environment fingerprint) to var/wizard-runs/<utc>/transcript.txt
# plus a structured summary.json. The recording becomes part of the
# truth-gate proof bundle so reviewers can prove the non-coder flow worked
# end-to-end on a clean clone.
#
# Usage:
#   bash scripts/wizard-record.sh                  # interactive wizard, recorded
#   bash scripts/wizard-record.sh --auto-yes       # accept all wizard prompts
#   bash scripts/wizard-record.sh --quick          # skip acceptance + UI launch
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

UTC="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="var/wizard-runs/${UTC}"
mkdir -p "$RUN_DIR"
TRANSCRIPT="$RUN_DIR/transcript.txt"
META="$RUN_DIR/summary.json"
ENV_FILE="$RUN_DIR/env.txt"
EXIT_FILE="$RUN_DIR/exit_code.txt"

AUTO_YES=0; QUICK=0
for arg in "$@"; do
  case "$arg" in
    --auto-yes) AUTO_YES=1 ;;
    --quick) QUICK=1 ;;
  esac
done

# Capture environment fingerprint up front (deterministic baseline)
{
  echo "timestamp_utc=$UTC"
  echo "host=$(hostname)"
  echo "user=$(whoami)"
  echo "cwd=$ROOT"
  command -v python >/dev/null && echo "python=$(python --version 2>&1)"
  command -v git    >/dev/null && echo "git=$(git --version)"
  command -v node   >/dev/null && echo "node=$(node --version)"
  echo "git_branch=$(git symbolic-ref --short HEAD 2>/dev/null || echo DETACHED)"
  echo "git_commit=$(git rev-parse HEAD)"
  echo "git_dirty=$(git diff --quiet && git diff --cached --quiet && echo no || echo yes)"
} > "$ENV_FILE"

START_NS="$(date +%s%N 2>/dev/null || echo 0)"

# Build the inner command as a single shell string (script -c takes one).
# Using a string (not an array) avoids the bash-array-to-string quote-loss
# bug that previously caused `bash -c bash <path>` to launch an interactive
# shell under script(1)'s pty, hanging CI.
if [ "$QUICK" -eq 1 ]; then
  INNER_CMD="bash $ROOT/scripts/preflight.sh && echo '(quick mode: skipped acceptance + UI)'"
else
  INNER_CMD="bash $ROOT/scripts/wizard.sh"
fi

# Non-interactive: WIZARD_AUTO_YES bypasses every wizard prompt. This is more
# robust than piping `yes` into stdin because `script(1)` creates a pty and
# `read` may read from /dev/tty bypassing the pipe.
if [ "$AUTO_YES" -eq 1 ]; then export WIZARD_AUTO_YES=1; fi

# `script(1)` records a typescript including TTY control bytes; we strip them after.
if command -v script >/dev/null 2>&1; then
  script -q -e -c "$INNER_CMD" "$TRANSCRIPT.raw" </dev/null >/dev/null
  EXIT_CODE=$?
  # Strip ANSI codes for the canonical transcript
  sed -E 's/\x1B\[[0-9;]*[A-Za-z]//g' "$TRANSCRIPT.raw" > "$TRANSCRIPT" 2>/dev/null || cp "$TRANSCRIPT.raw" "$TRANSCRIPT"
else
  # Fallback: no TTY control bytes, but works when script(1) is unavailable.
  bash -c "$INNER_CMD" </dev/null 2>&1 | tee "$TRANSCRIPT"
  EXIT_CODE=${PIPESTATUS[0]}
fi

END_NS="$(date +%s%N 2>/dev/null || echo 0)"
DURATION_S=$(( (END_NS - START_NS) / 1000000000 ))

echo "$EXIT_CODE" > "$EXIT_FILE"

# Build summary.json
{
  echo "{"
  echo "  \"timestamp_utc\": \"$UTC\","
  echo "  \"duration_seconds\": $DURATION_S,"
  echo "  \"exit_code\": $EXIT_CODE,"
  echo "  \"verdict\": \"$([ $EXIT_CODE -eq 0 ] && echo PASS || echo FAIL)\","
  echo "  \"transcript_path\": \"$TRANSCRIPT\","
  echo "  \"env_path\": \"$ENV_FILE\","
  echo "  \"flags\": { \"auto_yes\": $AUTO_YES, \"quick\": $QUICK }"
  echo "}"
} > "$META"

echo
echo "============================================================"
echo "Wizard recording: $RUN_DIR"
echo "Verdict: $([ $EXIT_CODE -eq 0 ] && echo PASS || echo FAIL)"
echo "Transcript: $TRANSCRIPT"
echo "Summary:    $META"
echo "============================================================"

exit $EXIT_CODE
