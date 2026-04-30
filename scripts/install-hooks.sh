#!/usr/bin/env bash
# Install Hermes3D project-local git hooks (A.5).
# Sets core.hooksPath to .githooks (project-scoped; does NOT modify global config).
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

hooks_dir=".githooks"
if [ ! -d "$hooks_dir" ]; then
  echo "ERROR: $hooks_dir not found at $repo_root" >&2
  exit 1
fi

git config core.hooksPath "$hooks_dir"

# Make hooks executable (Linux/macOS/WSL/Git-Bash)
chmod +x "$hooks_dir/pre-push" 2>/dev/null || true

if [ ! -x "$hooks_dir/pre-push" ]; then
  # On Windows filesystems +x may be a no-op; verify file exists at least.
  if [ ! -f "$hooks_dir/pre-push" ]; then
    echo "ERROR: $hooks_dir/pre-push missing." >&2
    exit 1
  fi
  echo "WARN: $hooks_dir/pre-push not marked executable (likely Windows FS). Git will still run it via sh." >&2
fi

echo "OK: core.hooksPath = $hooks_dir (project-local)"
echo "Installed hooks:"
ls -1 "$hooks_dir"
echo ""
echo "pre-push will:"
echo "  1. Refuse pushes to main/master"
echo "  2. Run 02-SCAFFOLDING/scripts/test.sh --fast before push"
