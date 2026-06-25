from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from agilang.cli_runtime import main as runtime_main


def test_blockchain_new_vendors_runtime_and_local_launchers(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    rc = runtime_main(["new", "Portable Chain", "--template", "blockchain", "--force"])
    assert rc == 0
    root = tmp_path / "portable-chain"
    assert (root / "vendor" / "agilang" / "__init__.py").exists()
    assert (root / "run.py").exists()
    assert (root / "chain.py").exists()
    assert (root / "rpc.py").exists()
    assert (root / "src" / "main.agi").exists()
    assert (root / "resources" / "views" / "explorer.ags").exists()
    assert not list((root / "scripts").glob("*.py")) if (root / "scripts").exists() else True


def test_vendored_generated_app_runs_without_global_import_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert runtime_main(["new", "Standalone Chain", "--template", "blockchain", "--force"]) == 0
    root = tmp_path / "standalone-chain"
    result = subprocess.run(
        [sys.executable, "run.py"],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "blockchain starter" in result.stdout.lower()


def test_no_vendor_flag_keeps_app_runtime_optional(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert runtime_main(["new", "Thin Chain", "--template", "blockchain", "--force", "--no-vendor"]) == 0
    root = tmp_path / "thin-chain"
    assert not (root / "vendor" / "agilang").exists()
    assert (root / "src" / "main.agi").exists()
