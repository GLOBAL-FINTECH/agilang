from __future__ import annotations

from pathlib import Path

from agilang.cli_runtime import main as runtime_main


def test_blockchain_new_vendors_runtime_and_agi_entrypoints(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    rc = runtime_main(["new", "Portable Chain", "--template", "blockchain", "--force"])
    assert rc == 0
    root = tmp_path / "portable-chain"
    assert (root / "vendor" / "agilang" / "__init__.py").exists()
    assert (root / "run.agi").exists()
    assert (root / "chain.agi").exists()
    assert (root / "rpc.agi").exists()
    assert not (root / "run.py").exists()
    assert not (root / "chain.py").exists()
    assert not (root / "rpc.py").exists()
    assert (root / "src" / "main.agi").exists()
    assert (root / "src" / "chain.agi").exists()
    assert (root / "src" / "rpc.agi").exists()
    assert (root / "resources" / "views" / "explorer.ags").exists()
    assert not list((root / "scripts").glob("*.py")) if (root / "scripts").exists() else True


def test_root_agi_entrypoints_delegate_to_src_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert runtime_main(["new", "Standalone Chain", "--template", "blockchain", "--force"]) == 0
    root = tmp_path / "standalone-chain"
    assert 'include("src/main.agi")' in (root / "run.agi").read_text(encoding="utf-8")
    assert 'include("src/chain.agi")' in (root / "chain.agi").read_text(encoding="utf-8")
    assert 'include("src/rpc.agi")' in (root / "rpc.agi").read_text(encoding="utf-8")


def test_no_vendor_flag_keeps_app_runtime_optional_but_still_agi_native(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert runtime_main(["new", "Thin Chain", "--template", "blockchain", "--force", "--no-vendor"]) == 0
    root = tmp_path / "thin-chain"
    assert not (root / "vendor" / "agilang").exists()
    assert (root / "src" / "main.agi").exists()
    assert not (root / "run.py").exists()
