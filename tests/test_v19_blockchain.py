from pathlib import Path
import subprocess
import sys
import os

from agilang.blockchain import (
    blockchain_capabilities,
    blockchain_config,
    blockchain_devnet,
    blockchain_node,
    blockchain_transaction,
)
from agilang.scaffold import create_project


def test_blockchain_capabilities_include_required_components():
    caps = blockchain_capabilities()
    assert "proof_of_stake" in caps["consensus"]
    assert "canonical_reorg" in caps["fork_choice"]
    assert "gossip_block" in caps["p2p_sync"]
    assert "validation" in caps["mempool"]


def test_node_mempool_block_production_and_db(tmp_path):
    cfg = blockchain_config(
        chain_id=1900,
        name="test-chain",
        validators={"alice": 70, "bob": 30},
        genesis_state={"balances": {"alice": 1000, "bob": 100}},
        slot_seconds=1,
    )
    node = blockchain_node(cfg, tmp_path / "chain.sqlite", "alice-node")
    tx = blockchain_transaction("alice", "bob", 10, nonce=1, gas_price=1)
    assert node.submit_tx(tx)["ok"] is True
    parent = node.head()
    slot = parent["slot"] + 1
    proposer = node.consensus.select_proposer(parent["hash"], slot)
    block = node.produce_block(proposer, slot)
    assert node.validate_block(block)["ok"] is True
    imported = node.import_block(block)
    assert imported["ok"] is True
    assert node.height() == 1
    assert node.mempool.size() == 0
    assert node.db.get_block(block["hash"])["hash"] == block["hash"]


def test_devnet_syncs_blocks_between_peers():
    cfg = blockchain_config(chain_id=1901, name="devnet", validators={"alice": 60, "bob": 40}, slot_seconds=1)
    net = blockchain_devnet(cfg, validators=["alice", "bob"])
    net.submit_tx(blockchain_transaction("alice", "bob", 1, nonce=1, gas_price=1))
    result = net.step()
    assert result["ok"] is True
    heights = {node["height"] for node in net.status()["nodes"]}
    assert heights == {1}


def test_cli_blockchain_demo_runs():
    proc = subprocess.run(
        [sys.executable, "-m", "agilang", "blockchain", "demo"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        timeout=20,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
    )
    assert proc.returncode == 0, proc.stderr
    assert '"consensus"' in proc.stdout
    assert '"block_hash"' in proc.stdout


def test_blockchain_project_scaffold_runs(tmp_path):
    result = create_project("chain lab", directory=tmp_path, template="blockchain")
    assert (result.root / "src/main.agi").exists()
    assert (result.root / "docs/BLOCKCHAIN_RUNBOOK.md").exists()
    assert (result.root / "src/chain.agi").exists()
    assert (result.root / "src/mempool.agi").exists()
    assert (result.root / "src/devnet.agi").exists()
    assert (result.root / "resources/views/home.ags").exists()
    assert (result.root / "resources/views/blockchain.ags").exists()
    assert (result.root / "resources/assets/css/app.css").exists()
    assert (result.root / "resources/assets/js/blockchain-runtime.js").exists()
    proc = subprocess.run(
        [sys.executable, "-m", "agilang", "run", "src/chain.agi"],
        cwd=result.root,
        text=True,
        capture_output=True,
        timeout=20,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
    )
    assert proc.returncode == 0, proc.stderr


def test_v193_consensus_capabilities_include_pos_dpo_dpos_and_dev():
    caps = blockchain_capabilities()
    assert "pos" in caps["consensus"]
    assert "delegated_proof_of_stake" in caps["consensus"]
    assert "dpo_alias" in caps["consensus"]
    assert "dev_consensus" in caps["consensus"]
    assert "required_block_signatures" in caps["mainnet_profile"]


def test_v193_dpo_dpos_consensus_produces_and_imports_block(tmp_path):
    cfg = blockchain_config(
        chain_id=1931,
        name="dpo-chain",
        consensus_mode="dpo",
        validators={"alice": 1, "bob": 1},
        delegates=["alice", "bob"],
        delegations={
            "voter-a": {"delegate": "alice", "stake": 90},
            "voter-b": {"delegate": "bob", "stake": 10},
        },
        genesis_state={"balances": {"alice": 100, "bob": 0}},
        strict_accounting=True,
        slot_seconds=1,
    )
    node = blockchain_node(cfg, tmp_path / "dpo.sqlite", "dpo-node")
    tx = blockchain_transaction("alice", "bob", 5, nonce=1, gas_price=1)
    assert node.submit_tx(tx)["ok"] is True
    parent = node.head()
    slot = parent["slot"] + 1
    proposer = node.consensus.select_proposer(parent["hash"], slot)
    block = node.produce_block(proposer, slot)
    assert node.validate_block(block)["ok"] is True
    imported = node.import_block(block)
    assert imported["ok"] is True
    assert node.status()["consensus"] == "dpos"
    assert node.db.get_state("balances")["bob"] == 5


def test_v193_dev_consensus_simulation_mode_syncs():
    cfg = blockchain_config(
        chain_id=1932,
        name="dev-consensus",
        consensus_mode="dev",
        validators={"dev-a": 1, "dev-b": 1},
        genesis_state={"balances": {"dev-a": 100, "dev-b": 0}},
        strict_accounting=True,
        slot_seconds=1,
    )
    net = blockchain_devnet(cfg, validators=["dev-a", "dev-b"])
    assert net.submit_tx(blockchain_transaction("dev-a", "dev-b", 3, nonce=1, gas_price=1))["ok"] is True
    result = net.step()
    assert result["ok"] is True
    assert {node["height"] for node in net.status()["nodes"]} == {1}
    assert {node["consensus"] for node in net.status()["nodes"]} == {"dev"}


def test_v193_mainnet_profile_requires_valid_block_signature(tmp_path):
    from agilang.blockchain import blockchain_mainnet_config

    cfg = blockchain_mainnet_config(
        chain_id=1933,
        name="signed-mainnet-profile",
        validators={"alice": 100, "bob": 50},
        validator_signing_keys={"alice": "alice-secret", "bob": "bob-secret"},
        genesis_state={"balances": {"alice": 100, "bob": 0}},
        slot_seconds=1,
    )
    node = blockchain_node(cfg, tmp_path / "mainnet.sqlite", "mainnet-node")
    assert node.status()["mainnet_profile"] is True
    tx = blockchain_transaction("alice", "bob", 7, nonce=1, gas_price=1)
    assert node.submit_tx(tx)["ok"] is True
    parent = node.head()
    slot = parent["slot"] + 1
    proposer = node.consensus.select_proposer(parent["hash"], slot)
    block = node.produce_block(proposer, slot)
    assert block.get("validator_signature", "").startswith("agisig:")
    assert node.validate_block(block)["ok"] is True

    tampered = dict(block)
    tampered["validator_signature"] = "agisig:alice:bad"
    tampered["hash"] = tampered["hash"]  # keep original hash; validation must fail before import
    report = node.validate_block(tampered)
    assert report["ok"] is False
    assert "invalid_validator_signature" in report["errors"] or "invalid_block_hash" in report["errors"]


def test_v193_consensus_simulation_runs_all_modes():
    from agilang.blockchain import blockchain_consensus_simulation

    result = blockchain_consensus_simulation()
    assert result["ok"] is True
    modes = {row["consensus_mode"] for row in result["scenarios"]}
    assert {"pos", "dpos", "dev"}.issubset(modes)
    assert any(row["mainnet_profile"] and row["signed"] for row in result["scenarios"])
