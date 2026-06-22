from agilang.ethereum_consensus_replica import (
    DEFAULT_SLOT_SECONDS,
    DEFAULT_SLOTS_PER_EPOCH,
    ethereum_consensus_capabilities,
    ethereum_consensus_check,
    ethereum_consensus_replica_config,
    ethereum_consensus_simulation,
)


def test_ethereum_pos_replica_is_default_for_ethereum_derived_forks():
    caps = ethereum_consensus_capabilities()
    assert caps["default_ethereum_derived_consensus"] == "ethereum-pos-replica"
    assert caps["slot_seconds"] == 12
    assert caps["slots_per_epoch"] == 32
    assert "lmd_ghost_style_head_choice" in caps["features"]
    assert "casper_ffg_style_finality" in caps["features"]


def test_replica_config_uses_ethereum_time_model():
    cfg = ethereum_consensus_replica_config(chain_id=901900)
    assert cfg.consensus == "ethereum-pos-replica"
    assert cfg.slot_seconds == DEFAULT_SLOT_SECONDS
    assert cfg.slots_per_epoch == DEFAULT_SLOTS_PER_EPOCH
    assert cfg.chain_id == 901900


def test_replica_check_accepts_private_chain_id():
    cfg = ethereum_consensus_replica_config(chain_id=901900)
    result = ethereum_consensus_check(cfg)
    assert result["ok"] is True
    assert result["ethereum_pos_replica_private_fork_ready"] is True
    assert result["network_runtime_isolation"] is True


def test_replica_check_rejects_public_ethereum_chain_id():
    cfg = ethereum_consensus_replica_config(chain_id=1)
    result = ethereum_consensus_check(cfg)
    assert result["ok"] is False
    assert any("custom/private chain ID" in error for error in result["errors"])


def test_replica_simulation_produces_proposer_and_attestation_events():
    cfg = ethereum_consensus_replica_config(chain_id=901900)
    result = ethereum_consensus_simulation(slots=4, config=cfg)
    assert result["ok"] is True
    assert result["consensus"] == "ethereum-pos-replica"
    assert result["slots_simulated"] == 4
    assert len(result["events"]) == 4
    assert "proposer" in result["events"][0]
    assert "committee" in result["events"][0]
    assert "head_vote" in result["events"][0]
