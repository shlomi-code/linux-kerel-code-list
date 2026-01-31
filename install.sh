#!/usr/bin/env bash
# Install script for Linux Kernel Module Lister
# Creates a Python venv and installs dependencies.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Require Python 3.8+
python_cmd=""
for cmd in python3.12 python3.11 python3.10 python3.9 python3.8 python3; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" -c 'import sys; print(sys.version_info.major, sys.version_info.minor)' 2>/dev/null) || continue
        read -r major minor <<< "$ver"
        if [[ "$major" -eq 3 && "$minor" -ge 8 ]]; then
            python_cmd="$cmd"
            break
        fi
    fi
done

if [[ -z "$python_cmd" ]]; then
    echo "Error: Python 3.8 or newer is required. Install it with your package manager (e.g. apt install python3.9)." >&2
    exit 1
fi

echo "Using: $python_cmd ($($python_cmd --version 2>&1))"

# Create venv if it doesn't exist
VENV_DIR="$SCRIPT_DIR/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment in $VENV_DIR ..."
    "$python_cmd" -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists at $VENV_DIR"
fi

# Install dependencies
echo "Installing dependencies from requirements.txt ..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt

echo ""
echo "Installation complete."
echo ""
echo "To use the tool:"
echo "  1. Activate the venv:  source $VENV_DIR/bin/activate"
echo "  2. Run the lister:     python list_kernel_modules.py [options]"
echo ""
echo "Or run without activating:  $VENV_DIR/bin/python list_kernel_modules.py [options]"
echo ""
