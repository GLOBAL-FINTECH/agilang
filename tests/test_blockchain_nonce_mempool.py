from agilang import blockchain_config, blockchain_node, blockchain_transaction


VALIDATOR = "validator-1"
ALICE = "0xalice"
BOB = "0xbob"


def make_node():
    cfg = blockchain_config(
        chain_id=1923,
        name="nonce-aware-test-chain",
        consensus_mode="dev",
        validators={VALIDATOR: 1},
        genesis_state={"balances": {ALICE: 10_000, BOB: 0}, "nonces": {ALICE: 0}},
        strict_accounting=True,
        enforce_nonce_order=True,
        slot_seconds=1,
        max_account_queue_gap=128,
    )
    return blockchain_node(cfg, ":memory:", "nonce-test-node")


def produce_until_empty(node):
    produced = []
    for _ in range(10):
        if node.mempool.size() == 0:
            break
        parent = node.head()
        slot = int(parent.get("slot", node.height())) + 1
        proposer = node.consensus.select_proposer(parent["hash"], slot)
        result = node.produce_and_import_block(proposer, slot)
        assert result["import"]["ok"], result
        produced.append(result["block"])
        if not result["block"].get("transactions"):
            break
    return produced


def transfer(nonce, value=1):
    return blockchain_transaction(ALICE, BOB, value, nonce=nonce, gas_price=1)


def test_concurrent_reversed_nonce_burst_confirms_all_transactions():
    node = make_node()

    for nonce in reversed(range(30)):
        report = node.submit_tx(transfer(nonce))
        assert report["ok"], report

    blocks = produce_until_empty(node)
    included = sum(len(block.get("transactions", [])) for block in blocks)

    assert included == 30
    assert node.mempool.size() == 0
    assert node.db.get_state("nonces", {})[ALICE] == 30
    balances = node.db.get_state("balances", {})
    assert balances[ALICE] == 10_000 - 30
    assert balances[BOB] == 30


def test_nonce_gap_queues_until_missing_nonce_is_filled():
    node = make_node()

    future = node.submit_tx(transfer(2))
    assert future["ok"]
    assert future["status"] == "queued"

    empty_block = produce_until_empty(node)[0]
    assert empty_block.get("transactions") == []
    assert node.mempool.size() == 1

    assert node.submit_tx(transfer(0))["ok"]
    assert node.submit_tx(transfer(1))["ok"]
    blocks = produce_until_empty(node)
    included = sum(len(block.get("transactions", [])) for block in blocks)

    assert included == 3
    assert node.db.get_state("nonces", {})[ALICE] == 3
    assert node.mempool.size() == 0


def test_duplicate_account_nonce_is_rejected_before_execution():
    node = make_node()

    first = node.submit_tx(transfer(0))
    assert first["ok"], first

    duplicate = node.submit_tx(transfer(0, value=2))
    assert not duplicate["ok"]
    assert "duplicate_account_nonce" in duplicate["errors"]


def test_nonce_too_low_is_rejected_without_state_mutation():
    node = make_node()

    assert node.submit_tx(transfer(0))["ok"]
    produce_until_empty(node)

    before_balances = dict(node.db.get_state("balances", {}))
    before_nonces = dict(node.db.get_state("nonces", {}))

    too_low = node.submit_tx(transfer(0))
    assert not too_low["ok"]
    assert any(error.startswith("nonce_too_low") for error in too_low["errors"])

    assert node.db.get_state("balances", {}) == before_balances
    assert node.db.get_state("nonces", {}) == before_nonces
