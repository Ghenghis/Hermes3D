#!/usr/bin/env bash
# Hermes3D Non-Coder Wizard — guided zero-to-running flow.
# Goal: a non-technical user can run this once and see the desk-organizer in the UI.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

green(){ printf "\033[32m%s\033[0m\n" "$*"; }
red(){   printf "\033[31m%s\033[0m\n" "$*"; }
yel(){   printf "\033[33m%s\033[0m\n" "$*"; }
blue(){  printf "\033[36m%s\033[0m\n" "$*"; }
hr(){    printf '%s\n' "------------------------------------------------------------"; }

ask(){ # ask "prompt" default
  local prompt="$1"; local default="${2:-y}"
  read -r -p "$prompt [$default] " ans
  ans="${ans:-$default}"
  [[ "$ans" =~ ^[Yy] ]]
}

clear || true
blue "================================================================"
blue "  Hermes3D-OS Lite — Setup Wizard"
blue "  Goal: from clean machine to first desk-organizer in the UI"
blue "================================================================"
echo
yel "This wizard will:"
echo  "  1. Validate your environment (Python, git, node)"
echo  "  2. Install Hermes3D + dependencies"
echo  "  3. Install pre-push git hooks (branch discipline)"
echo  "  4. Run the acceptance test suite"
echo  "  5. Launch the Gradio UI in your browser"
echo
ask "Proceed?" "y" || { echo "Cancelled."; exit 0; }

hr
blue "Step 1/5  Preflight"
hr
if ! bash "$ROOT/scripts/preflight.sh"; then
  red "Preflight failed. Fix the missing tools listed above, then re-run."
  exit 1
fi

hr
blue "Step 2/5  Installing Hermes3D (editable + UI extras)"
hr
if [[ ! -f "$ROOT/02-SCAFFOLDING/pyproject.toml" && ! -f "$ROOT/pyproject.toml" ]]; then
  red "pyproject.toml not found. Wrong working directory?"
  exit 1
fi
PYPROJECT_DIR="$ROOT"
[[ -f "$ROOT/02-SCAFFOLDING/pyproject.toml" ]] && PYPROJECT_DIR="$ROOT/02-SCAFFOLDING"
(cd "$PYPROJECT_DIR" && python -m pip install -e ".[all]" 2>&1 | tail -8) || {
  yel "[.all] extras not available — falling back to base install"
  (cd "$PYPROJECT_DIR" && python -m pip install -e . 2>&1 | tail -8)
}

hr
blue "Step 3/5  Installing branch-discipline git hooks"
hr
if [[ -f "$ROOT/scripts/install-hooks.sh" ]]; then
  bash "$ROOT/scripts/install-hooks.sh" || yel "Hook install reported issues; continuing."
else
  yel "scripts/install-hooks.sh not found yet (added by sibling task A.5). Skipping."
fi

hr
blue "Step 4/5  Acceptance suite (48 cells)"
hr
if [[ -f "$ROOT/04-TEST-CASE-DESK-ORGANIZER/run_acceptance.py" ]]; then
  python "$ROOT/04-TEST-CASE-DESK-ORGANIZER/run_acceptance.py" 2>&1 | tail -10 || {
    red "Acceptance run failed. See output above."
    yel "You can still continue to step 5; some cells may rely on optional tools."
    ask "Continue to UI launch?" "y" || exit 1
  }
else
  yel "Acceptance runner not found at expected path. Skipping."
fi

hr
blue "Step 5/5  Launching Gradio UI"
hr
green "Opening http://localhost:7860 in your browser..."
green "(The Gradio launcher will run in this terminal. Press Ctrl+C to stop.)"
echo
sleep 1

# Best-effort browser open
URL="http://localhost:7860"
if command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then open "$URL" >/dev/null 2>&1 &
elif command -v cmd.exe >/dev/null 2>&1; then cmd.exe /c start "$URL" >/dev/null 2>&1 &
fi

# Run launcher (foreground)
python -m hermes3d.app.launcher
