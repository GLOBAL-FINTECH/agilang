#!/usr/bin/env sh
# AGILANG CLI installer for Linux and macOS.
# Run:
#   sh scripts/install_unix.sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PACKAGE_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "Python 3.10+ was not found. Install Python and make sure python3 is on PATH." >&2
  exit 1
fi

echo "Installing AGILANG CLI from $PACKAGE_ROOT"
"$PYTHON" "$PACKAGE_ROOT/install.py"
echo "AGILANG CLI installer finished."
