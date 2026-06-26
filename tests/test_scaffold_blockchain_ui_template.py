"""Test blockchain template scaffold generation with UI."""
from pathlib import Path
import subprocess
import sys
import os

from agilang.scaffold import create_project


def test_blockchain_template_generates_web_ui(tmp_path):
    """Blockchain template should generate web UI with AGS templates."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    root = result.root

    # Core blockchain files
    assert (root / "src/main.agi").exists()
    assert (root / "src/chain.agi").exists()
    assert (root / "src/mempool.agi").exists()
    assert (root / "src/devnet.agi").exists()

    # Web UI files
    assert (root / "resources/views/layout.ags").exists()
    assert (root / "resources/views/home.ags").exists()
    assert (root / "resources/views/blockchain.ags").exists()

    # Assets
    assert (root / "resources/assets/css/app.css").exists()
    assert (root / "resources/assets/js/blockchain-runtime.js").exists()

    # Documentation
    assert (root / "docs/BLOCKCHAIN_RUNBOOK.md").exists()


def test_blockchain_template_home_ags_contains_fetch_directive(tmp_path):
    """Blockchain template home.ags should contain @fetch directive for live data."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    home_ags = (result.root / "resources/views/home.ags").read_text(encoding="utf-8")
    assert "@fetch" in home_ags
    assert "chain" in home_ags
    assert "blocks" in home_ags


def test_blockchain_template_main_contains_api_routes(tmp_path):
    """Blockchain template main.agi should contain blockchain API routes."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    main_agi = (result.root / "src/main.agi").read_text(encoding="utf-8")
    assert "/blockchain" in main_agi
    assert "/api/submit-tx" in main_agi
    assert "/api/produce-block" in main_agi
    assert "json_response" in main_agi


def test_blockchain_template_blockchain_ags_contains_loop(tmp_path):
    """Blockchain template blockchain.ags should contain loop directive for blocks/txs."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    blockchain_ags = (result.root / "resources/views/blockchain.ags").read_text(encoding="utf-8")
    assert "@fetch" in blockchain_ags
    assert "for" in blockchain_ags.lower()
    assert "blocks" in blockchain_ags
    assert "transactions" in blockchain_ags or "tx" in blockchain_ags.lower()


def test_blockchain_template_css_exists_and_has_styling(tmp_path):
    """Blockchain template CSS should contain styling rules."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    css = (result.root / "resources/assets/css/app.css").read_text(encoding="utf-8")
    assert ":root" in css or "body" in css


def test_blockchain_template_js_runtime_exists(tmp_path):
    """Blockchain template JS runtime should exist and contain fetch logic."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    js = (result.root / "resources/assets/js/blockchain-runtime.js").read_text(encoding="utf-8")
    assert "fetch" in js
    assert "updateElement" in js or "hydrate" in js


def test_blockchain_template_passes_agi_check(tmp_path):
    """Blockchain template should pass agi check on chain.agi."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    proc = subprocess.run(
        [sys.executable, "-m", "agilang", "check", "src/chain.agi"],
        cwd=result.root,
        text=True,
        capture_output=True,
        timeout=20,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
    )
    # agi check may have warnings but should not crash
    assert proc.returncode == 0, proc.stderr


def test_blockchain_template_main_agi_has_web_app(tmp_path):
    """Blockchain template main.agi should include web app for UI."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    main_agi = (result.root / "src/main.agi").read_text(encoding="utf-8")
    assert "web_app" in main_agi or "create_app" in main_agi


def test_blockchain_template_storage_dir_exists(tmp_path):
    """Blockchain template should create storage directory for database."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    assert (result.root / "storage/.gitkeep").exists()


def test_blockchain_template_config_files_exist(tmp_path):
    """Blockchain template should include config files for validators."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    assert (result.root / "config/validators.json").exists()
