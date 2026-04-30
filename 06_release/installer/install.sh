#!/usr/bin/env bash
# 06_release/installer/install.sh — Hermes3D-OS Lite installer (Linux / WSL).

set -u

INSTALLER_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$INSTALLER_DIR/../.." && pwd)"
SCAFFOLDING="$REPO_ROOT/03_implementation"

COMPONENTS=""
NO_VERIFY=0
QUIET=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --components) COMPONENTS="$2"; shift 2 ;;
        --no-verify) NO_VERIFY=1; shift ;;
        --quiet) QUIET=1; shift ;;
        --help|-h)
            cat <<'EOF'
Usage: install.sh [--components LIST|all|minimal] [--quiet] [--no-verify]

Examples:
  install.sh                                # interactive
  install.sh --components all
  install.sh --components gradio_ui,rest_api --quiet
EOF
            exit 0
            ;;
        *) echo "[FAIL] unknown arg: $1"; exit 1 ;;
    esac
done

echo "================================================================"
echo "  Hermes3D-OS Lite Installer (v5)"
echo "================================================================"

if [[ ! -f "$INSTALLER_DIR/manifest.json" ]]; then
    echo "[FAIL] manifest.json not found at $INSTALLER_DIR" >&2
    exit 1
fi

PY=""
for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then PY="$cmd"; break; fi
done
if [[ -z "$PY" ]]; then
    echo "[FAIL] Python 3.11+ required. Install via your package manager." >&2
    exit 1
fi
PY_VER="$($PY -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}")')"
echo "[1/5] Python: $PY_VER ($PY)"

# Read component keys from manifest using the same Python interpreter
KEYS=$($PY -c 'import json,sys; m=json.load(open(sys.argv[1])); print(" ".join(m["components"].keys()))' "$INSTALLER_DIR/manifest.json")

declare -A CHOSEN
for key in $KEYS; do
    REQUIRED=$($PY -c "import json,sys; print(json.load(open(sys.argv[1]))['components']['$key'].get('required',False))" "$INSTALLER_DIR/manifest.json")
    DEFAULT=$($PY -c "import json,sys; print(json.load(open(sys.argv[1]))['components']['$key'].get('default',False))" "$INSTALLER_DIR/manifest.json")
    DESC=$($PY -c "import json,sys; print(json.load(open(sys.argv[1]))['components']['$key'].get('description',''))" "$INSTALLER_DIR/manifest.json")

    if [[ "$REQUIRED" == "True" ]]; then
        CHOSEN[$key]=1
        continue
    fi
    if [[ "$COMPONENTS" == "all" ]]; then
        CHOSEN[$key]=1; continue
    fi
    if [[ "$COMPONENTS" == "minimal" ]]; then
        CHOSEN[$key]=0; continue
    fi
    if [[ -n "$COMPONENTS" ]]; then
        if [[ ",$COMPONENTS," == *,$key,* ]]; then CHOSEN[$key]=1; else CHOSEN[$key]=0; fi
        continue
    fi
    if [[ "$QUIET" -eq 1 ]]; then
        if [[ "$DEFAULT" == "True" ]]; then CHOSEN[$key]=1; else CHOSEN[$key]=0; fi
        continue
    fi
    if [[ "$DEFAULT" == "True" ]]; then prompt="[Y/n]"; else prompt="[y/N]"; fi
    read -r -p "  Install '$key' ($DESC)? $prompt " resp
    if [[ -z "$resp" ]]; then
        if [[ "$DEFAULT" == "True" ]]; then CHOSEN[$key]=1; else CHOSEN[$key]=0; fi
    elif [[ "$resp" =~ ^[Yy] ]]; then
        CHOSEN[$key]=1
    else
        CHOSEN[$key]=0
    fi
done

echo
echo "[2/5] Installing core package + dependencies ..."
cd "$SCAFFOLDING"
$PY -m pip install --upgrade pip
$PY -m pip install -r requirements.txt
$PY -m pip install -e .

echo
echo "[3/5] Installing optional components ..."
for key in $KEYS; do
    if [[ "${CHOSEN[$key]:-0}" -ne 1 ]]; then continue; fi
    REQUIRED=$($PY -c "import json,sys; print(json.load(open(sys.argv[1]))['components']['$key'].get('required',False))" "$INSTALLER_DIR/manifest.json")
    if [[ "$REQUIRED" == "True" ]]; then continue; fi
    INSTALL_CMD=$($PY -c "import json,sys; print(json.load(open(sys.argv[1]))['components']['$key'].get('install',''))" "$INSTALLER_DIR/manifest.json")
    EXTERNAL=$($PY -c "import json,sys; print(json.load(open(sys.argv[1]))['components']['$key'].get('external_setup',''))" "$INSTALLER_DIR/manifest.json")
    CREDS=$($PY -c "import json,sys; print(','.join(json.load(open(sys.argv[1]))['components']['$key'].get('credentials_required',[])))" "$INSTALLER_DIR/manifest.json")

    echo "  + $key — $INSTALL_CMD"
    eval "$INSTALL_CMD" || echo "    [WARN] $key install failed; continuing."
    [[ -n "$EXTERNAL" ]] && echo "    note: external setup at $EXTERNAL"
    [[ -n "$CREDS" ]] && echo "    note: set these env vars: $CREDS"
done

echo
echo "[4/5] Creating runtime directories ..."
DIRS=$($PY -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1]))["directories_created"]))' "$INSTALLER_DIR/manifest.json")
for d in $DIRS; do
    full="$SCAFFOLDING/${d#./}"
    mkdir -p "$full"
    echo "  + $d"
done

if [[ "$NO_VERIFY" -eq 1 ]]; then
    echo
    echo "[5/5] verification skipped (--no-verify)"
else
    echo
    echo "[5/5] running verify_install.py ..."
    $PY "$INSTALLER_DIR/verify_install.py"
    rc=$?
    if [[ $rc -ne 0 ]]; then
        echo "[FAIL] verification failed."
        exit 1
    fi
fi

echo
echo "================================================================"
echo "  Install complete."
echo "  Next steps:"
$PY -c 'import json; m=json.load(open(r"'"$INSTALLER_DIR"'/manifest.json")); [print(f"    - {s}") for s in m["post_install_steps"]]'
echo "================================================================"
