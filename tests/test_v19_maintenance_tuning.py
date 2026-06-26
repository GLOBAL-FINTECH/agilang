from pathlib import Path

from agilang import __version__
from agilang.blockchain import blockchain_config, blockchain_node, blockchain_transaction
from agilang.hybrid_runtime import RUNTIME_VERSION


def test_native_runtime_version_tracks_package_release():
    assert __version__ == "2.1.0"
    assert RUNTIME_VERSION == __version__


def test_mempool_rejects_duplicate_transaction_hash():
    node = blockchain_node(blockchain_config(validators={"alice": 100}, slot_seconds=1))
    tx = blockchain_transaction("alice", "bob", 1, nonce=1, gas_price=1)
    assert node.submit_tx(tx)["ok"] is True
    duplicate = node.submit_tx(tx)
    assert duplicate["ok"] is False
    assert "duplicate_tx_hash" in duplicate["errors"]
    assert node.mempool.size() == 1


def test_strict_accounting_validates_balance_and_rebuilds_state(tmp_path: Path):
    cfg = blockchain_config(
        chain_id=1911,
        name="strict-chain",
        validators={"alice": 100},
        genesis_state={"balances": {"alice": 50, "bob": 0}},
        strict_accounting=True,
        slot_seconds=1,
    )
    node = blockchain_node(cfg, tmp_path / "strict.sqlite", "alice-node")
    bad = blockchain_transaction("alice", "bob", 100, nonce=1, gas_price=1)
    rejected = node.submit_tx(bad)
    assert rejected["ok"] is False
    assert "insufficient_balance" in rejected["errors"]

    good = blockchain_transaction("alice", "bob", 25, nonce=1, gas_price=1)
    assert node.submit_tx(good)["ok"] is True
    slot = node.head()["slot"] + 1
    proposer = node.consensus.select_proposer(node.head()["hash"], slot)
    block = node.produce_block(proposer, slot)
    imported = node.import_block(block)
    assert imported["ok"] is True
    assert node.db.get_state("balances")["alice"] == 25
    assert node.db.get_state("balances")["bob"] == 25
    assert node.db.get_state("nonces")["alice"] == 1


def test_strict_accounting_rejects_imported_invalid_state_transition():
    from agilang.blockchain import blockchain_merkle_root, _now_ms, _sha256_hex

    cfg = blockchain_config(
        chain_id=1912,
        name="strict-import-chain",
        validators={"alice": 100},
        genesis_state={"balances": {"alice": 50, "bob": 0}},
        strict_accounting=True,
        slot_seconds=1,
    )
    node = blockchain_node(cfg, node_id="alice-node")
    parent = node.head()
    slot = parent["slot"] + 1
    proposer = node.consensus.select_proposer(parent["hash"], slot)
    tx = blockchain_transaction("alice", "bob", 100, nonce=1, gas_price=1)
    forged_receipts = [{"tx_hash": tx["hash"], "ok": True, "gas_used": 21000, "error": ""}]
    forged_state = {"balances": {"alice": -50, "bob": 100}, "contracts": {}, "nonces": {"alice": 1}}
    block = {
        "chain_id": cfg.chain_id,
        "height": 1,
        "slot": slot,
        "parent_hash": parent["hash"],
        "proposer": proposer,
        "timestamp_ms": _now_ms(),
        "transactions": [tx],
        "receipts": forged_receipts,
        "tx_root": blockchain_merkle_root([tx]),
        "state_updates": forged_state,
        "state_root": _sha256_hex(forged_state),
        "receipts_root": blockchain_merkle_root(forged_receipts),
        "gas_used": 21000,
        "score": 100 + 100,
        "extra_data": {"node_id": "malicious"},
    }
    block["hash"] = _sha256_hex({k: v for k, v in block.items() if k != "hash"})

    rejected = node.import_block(block)
    assert rejected["ok"] is False
    assert "invalid_receipts" in rejected["errors"]
    assert "invalid_state_updates" in rejected["errors"]
    assert node.db.get_state("balances") == {"alice": 50, "bob": 0}
