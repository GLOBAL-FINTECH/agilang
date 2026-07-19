from __future__ import annotations

import json

from agilang.smart_chain_cli import create_project


def test_blockchain_cli_scaffold_includes_compatible_frontend(tmp_path):
    result = create_project("frontend-chain", directory=tmp_path, template="blockchain")
    root = result.root

    assert (root / "frontend/index.html").is_file()
    assert (root / "frontend/assets/dashboard.css").is_file()
    assert (root / "frontend/assets/dashboard.js").is_file()

    contract = json.loads((root / "frontend/api-contract.json").read_text(encoding="utf-8"))
    assert contract["status"] == "/api/status"
    assert contract["operations_live"] == "/api/operations/live"
    assert contract["contract_builder"] == "/contracts/builder"

    html = (root / "frontend/index.html").read_text(encoding="utf-8")
    js = (root / "frontend/assets/dashboard.js").read_text(encoding="utf-8")
    assert "Chain ID" in html
    assert "1990" in html
    assert "/transactions" in html
    assert "/validators" in html
    assert "/beacon" in html
    assert "/peers" in html
    assert "get('/api/status')" in js
    assert "get('/api/operations/live')" in js


def test_evm_alias_gets_same_frontend(tmp_path):
    result = create_project("evm-frontend", directory=tmp_path, template="evm")
    assert (result.root / "frontend/api-contract.json").is_file()
