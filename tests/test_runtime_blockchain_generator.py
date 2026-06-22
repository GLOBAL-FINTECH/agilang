from pathlib import Path
import json

from agilang.blockchain_runtime_gateway import generate_blockchain_app, chain_status


def test_runtime_generator_creates_complete_blockchain_app(tmp_path):
    result = generate_blockchain_app("My Chain", tmp_path, force=True)
    root = Path(result["root"])
    assert (root / "src/main.agi").exists()
    assert (root / "src/chain.agi").exists()
    assert (root / "config/rpc.json").exists()
    assert (root / "config/network.json").exists()
    assert (root / "config/ethereum-clients.json").exists()
    assert (root / "docs/METAMASK_SETUP.md").exists()
    assert "config/wallets/*.key" in (root / ".gitignore").read_text()
    rpc = json.loads((root / "config/rpc.json").read_text())
    assert rpc["chain"]["chain_id"] == 1900
    assert rpc["chain"]["mainnet_profile"] is True
    assert rpc["chain"]["require_block_signatures"] is True


def test_project_chain_status_loads_generated_config(tmp_path):
    result = generate_blockchain_app("Status Chain", tmp_path, force=True)
    status = chain_status(result["root"])
    assert status["ok"] is True
    assert status["status"]["chain_id"] == 1900
    assert status["status"]["consensus"] == "pos"
