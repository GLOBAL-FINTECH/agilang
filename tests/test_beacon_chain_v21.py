from pathlib import Path

from agilang.beacon import (
    BeaconAttestation,
    BeaconConfig,
    BeaconStore,
    attest_to_head,
    beacon_capabilities,
    create_beacon_state,
    detect_slashable_events,
    fork_choice_head,
    init_beacon_runtime,
    process_epoch_finality,
    produce_beacon_block,
    simulate_beacon,
)


def test_beacon_capabilities_are_native_sbq_not_ethereum_mainnet():
    caps = beacon_capabilities()
    assert caps["consensus"] == "sbq-beacon"
    assert caps["ethereum_mainnet_replacement"] is False
    assert "checkpoint_finalization" in caps["features"]


def test_slots_epochs_block_attestations_and_finality():
    state = create_beacon_state(BeaconConfig(slot_seconds=6, slots_per_epoch=4))
    block = produce_beacon_block(state)
    assert block.slot == 1
    assert block.epoch == 0
    assert block.execution_payload.block_number == 1

    attestations = attest_to_head(state)
    assert len(attestations) == len(state.active_validators())

    # Produce through the first epoch boundary and finalize.
    for _ in range(3):
        produce_beacon_block(state)
        attest_to_head(state)

    result = process_epoch_finality(state)
    assert result["ok"] is True
    assert result["justified"] is True
    assert state.justified_checkpoint.epoch == 1


def test_fork_choice_selects_attested_head():
    state = create_beacon_state(BeaconConfig(slots_per_epoch=4))
    block = produce_beacon_block(state)
    attest_to_head(state)
    result = fork_choice_head(state)
    assert result["ok"] is True
    assert result["head"] == block.root


def test_double_vote_detection():
    att1 = BeaconAttestation("0xabc", 1, 0, 1, "0x" + "11" * 32)
    att2 = BeaconAttestation("0xabc", 1, 0, 1, "0x" + "22" * 32)
    result = detect_slashable_events([], [att1, att2])
    assert result["count"] == 1
    assert result["slashable"][0]["type"] == "double_vote"


def test_sqlite_store_roundtrip(tmp_path: Path):
    store = BeaconStore(tmp_path / "beacon.sqlite")
    state = create_beacon_state(BeaconConfig(slots_per_epoch=4))
    produce_beacon_block(state)
    attest_to_head(state)
    store.save_state(state)

    loaded = store.load_state()
    assert loaded.current_slot == state.current_slot
    assert loaded.head_root == state.head_root
    assert len(loaded.blocks) == 1
    assert len(loaded.validators) == len(state.validators)


def test_runtime_initialization_writes_config_and_store(tmp_path: Path):
    result = init_beacon_runtime(tmp_path, BeaconConfig(chain_id=1900))
    assert result["ok"] is True
    assert (tmp_path / "config/beacon.json").exists()
    assert (tmp_path / "storage/beacon.sqlite").exists()


def test_simulation_runs_multiple_epochs_and_finalizes():
    result = simulate_beacon(validators=8, epochs=3, slots_per_epoch=4)
    assert result["ok"] is True
    assert result["slots"] == 12
    assert result["justified_checkpoint"]["epoch"] >= 1
    assert result["finalized_checkpoint"]["epoch"] >= 0
