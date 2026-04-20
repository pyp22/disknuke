#!/bin/bash
# Author: Pierre-Yves PARANTHOEN
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/dd_wipe.py"

# --- Root check ---
if [ "$EUID" -ne 0 ]; then
    echo "Re-launching with sudo..."
    exec sudo bash "$0" "$@"
fi

# --- System dependencies ---
MISSING=()

# Python 3.6+
if ! command -v python3 &>/dev/null; then
    MISSING+=("python3")
else
    PY_VER=$(python3 -c 'import sys; print(sys.version_info >= (3,6))' 2>/dev/null)
    if [ "$PY_VER" != "True" ]; then
        echo "ERROR: python3 >= 3.6 is required." >&2
        exit 1
    fi
fi

for cmd in dd blockdev sync; do
    command -v "$cmd" &>/dev/null || MISSING+=("$cmd")
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "ERROR: missing commands: ${MISSING[*]}" >&2
    echo ""

    # Attempt automatic installation (Debian/Ubuntu)
    if command -v apt-get &>/dev/null; then
        echo "Installing via apt-get..."
        PKG_MAP=( ["python3"]="python3" ["dd"]="coreutils" ["blockdev"]="util-linux" ["sync"]="coreutils" )
        PKGS=()
        for cmd in "${MISSING[@]}"; do
            pkg="${PKG_MAP[$cmd]:-$cmd}"
            PKGS+=("$pkg")
        done
        apt-get install -y "${PKGS[@]}"
    else
        echo "Please install manually: ${MISSING[*]}" >&2
        exit 1
    fi
fi

# --- Python script check ---
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "ERROR: $PYTHON_SCRIPT not found." >&2
    exit 1
fi

chmod +x "$PYTHON_SCRIPT"

# --- Launch ---
exec python3 "$PYTHON_SCRIPT" "$@"
