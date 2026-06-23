#!/usr/bin/env python3
"""Cross-platform AGILANG CLI installer.

Run from any location:
    python install.py

The script installs the AGILANG package from this repository globally for the
current Python environment, then verifies the agilang and agi commands.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path
import tomllib


PACKAGE_ROOT = Path(__file__).resolve().parent
PYPROJECT = PACKAGE_ROOT / "pyproject.toml"


def expected_version() -> str:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print(f"> {' '.join(command)}", flush=True)
    return subprocess.run(command, check=check, text=True)


def command_output(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return completed.stdout.strip()


def ensure_supported_python() -> None:
    if sys.version_info < (3, 10):
        raise SystemExit("AGILANG requires Python 3.10 or newer.")


def install_package() -> None:
    python = sys.executable
    run([python, "-m", "pip", "install", "--upgrade", "pip"])
    run([python, "-m", "pip", "install", "--upgrade", str(PACKAGE_ROOT)])


def verify_command(command: str, expected_version: str) -> bool:
    executable = shutil.which(command)
    if executable is None:
        print(f"{command}: not found on PATH")
        return False

    output = command_output([command, "--version"])
    print(f"{command}: {output} ({executable})")
    return expected_version in output


def print_path_help() -> None:
    scripts_dir = Path(sys.executable).resolve().parent
    system = platform.system().lower()

    if system == "windows":
        scripts_dir = scripts_dir / "Scripts"
        print("\nIf agilang or agi is not available in a new terminal, add this to PATH:")
        print(f"  {scripts_dir}")
        print("Then restart PowerShell or Command Prompt.")
        return

    user_base = command_output([sys.executable, "-m", "site", "--user-base"])
    user_bin = Path(user_base) / "bin"
    candidates = [scripts_dir, user_bin]
    print("\nIf agilang or agi is not available in a new terminal, add one of these to PATH:")
    for candidate in candidates:
        print(f"  {candidate}")
    print("Then restart your shell.")


def main() -> int:
    system = platform.system() or "Unknown"
    version = expected_version()
    print(f"Installing AGILANG CLI {version} on {system}", flush=True)
    print(f"Package root: {PACKAGE_ROOT}", flush=True)

    ensure_supported_python()
    install_package()

    print("\nVerifying CLI commands...")
    ok = verify_command("agilang", version) and verify_command("agi", version)

    if not ok:
        print_path_help()
        return 1

    print("\nAGILANG CLI installation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
