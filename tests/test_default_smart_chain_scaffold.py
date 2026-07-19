from __future__ import annotations

import json
from pathlib import Path

from agilang.smart_chain_scaffold import create_project


def test_blockchain_template_generates_complete_smart_chain(tmp_path: Path) -> None:
    result = create_project("developer-chain", directory=tmp_path, template="blockchain")
    root = result.root

    assert result.template == "blockchain"
    assert json.loads((root / "config/network.json").read_text(encoding="utf-8"))["chain_id"] == 1990
    assert json.loads((root / "config/metamask.json").read_text(encoding="utf-8"))["chainId"] == "0x7c6"
    assert (root / "config/chain-services.json").exists()
    assert (root / "config/beacon.json").exists()
    assert (root / "config/validators.json").exists()
    assert (root / "config/p2p.json").exists()
    assert (root / "config/slashing.json").exists()
    assert (root / "scripts/rpc_gate.py").exists()
    assert (root / "scripts/readiness.py").exists()
    assert (root / "start-chain.ps1").exists()
    assert (root / "start-chain.sh").exists()
    assert (root / "vendor/agilang/inhouse_chain.py").exists()
    assert "complete default blockchain application" in (root / "README.md").read_text(encoding="utf-8")


def test_evm_alias_also_generates_smart_chain(tmp_path: Path) -> None:
    result = create_project("evm-chain", directory=tmp_path, template="evm")
    assert result.template == "blockchain"
    assert (result.root / "config/chain-services.json").exists()
