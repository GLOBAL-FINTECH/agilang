#!/usr/bin/env sh
# AGILANG CLI installer for macOS.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
sh "$SCRIPT_DIR/install_unix.sh"
