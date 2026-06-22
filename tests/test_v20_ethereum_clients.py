import json
import subprocess
import sys
from pathlib import Path

from agilang.ethereum_clients import (
    default_ethereum_client_config,
    ethereum_client_capabilities,
    ethereum_stack_plan,
    ethereum_stack_check,
    load_ethereum_client_config,
    validate_ethereum_client_config,
    write_ethereum_client_config,
)
from agilang.network_runtime import chain_start_plan, default_network_config, network_mode_matrix, network_runtime_check
from agilang.blockchain import ethereum_network_compatibility_check, blockchain_capabilities


def test_ethereum_client_capabilities_expose_real_client_roles():
    caps = ethereum_client_capabilities()
    assert "geth" in caps["supported_execution_clients"]
    assert "lighthouse" in caps["supported_consensus_clients"]
    assert caps["ethereum_truth_boundary"]["ethereum_validation_requires_external_consensus_and_validator_clients"] is True
    assert caps["ethereum_truth_boundary"]["native_agilang_custom_consensus_can_validate_ethereum_mainnet"] is False


def test_full_ethereum_stack_plan_has_execution_and_consensus_commands():
    cfg = default_ethereum_client_config(mode="full", execution_client="geth", consensus_client="lighthouse")
    plan = ethereum_stack_plan(cfg)
    assert plan["ok"] is True
    assert "execution" in plan["commands"]
    assert "consensus" in plan["commands"]
    assert "validator" not in plan["commands"]
    assert "--authrpc.jwtsecret" in plan["commands"]["execution"]
    assert "--execution-endpoint" in plan["commands"]["consensus"]


def test_archive_plan_enables_geth_archive_flags():
    cfg = default_ethereum_client_config(mode="archive", execution_client="geth", consensus_client="lighthouse")
    plan = ethereum_stack_plan(cfg, mode="archive")
    command = plan["commands"]["execution"]
    assert plan["archive"] is True
    assert "--gcmode=archive" in command
    assert "full" in command


def test_validator_mode_keeps_validator_http_private():
    cfg = default_ethereum_client_config(mode="validator", validator_enabled=True, fee_recipient="0x0000000000000000000000000000000000000000")
    validation = validate_ethereum_client_config(cfg)
    plan = ethereum_stack_plan(cfg)
    assert validation["ok"] is True
    assert validation["validator_private"] is True
    assert "validator" in plan["commands"]
    assert "--suggested-fee-recipient" in plan["commands"]["validator"]


def test_write_and_load_ethereum_client_config(tmp_path):
    config_path = tmp_path / "ethereum-clients.json"
    result = write_ethereum_client_config(config_path, mode="all", archive=True, validator_enabled=True, fee_recipient="0x0000000000000000000000000000000000000000")
    assert result["ok"] is True
    loaded = load_ethereum_client_config(config_path)
    assert loaded.mode == "all"
    assert loaded.archive is True
    assert loaded.validator_enabled is True
    assert loaded.fee_recipient.startswith("0x")


def test_network_runtime_includes_ethereum_client_profiles():
    modes = network_mode_matrix()["modes"]
    assert "ethereum-full" in modes
    assert "ethereum-archive" in modes
    assert "ethereum-validator" in modes
    assert "ethereum-all" in modes
    assert chain_start_plan(default_network_config(), mode="ethereum-all")["ethereum_client_stack"]["validator_enabled"] is True


def test_network_runtime_check_includes_ethereum_client_stack():
    check = network_runtime_check()
    assert check["ok"] is True
    assert check["checks"]["ethereum_execution_client_plan"] is True
    assert check["checks"]["ethereum_consensus_client_plan"] is True


def test_blockchain_ethereum_compatibility_mentions_external_clients():
    payload = ethereum_network_compatibility_check()
    assert payload["ok"] is True
    assert payload["can_orchestrate_ethereum_execution_client"] is True
    assert payload["can_orchestrate_ethereum_consensus_client"] is True
    assert payload["can_validate_ethereum_mainnet_with_agilang_custom_consensus"] is False
    caps = blockchain_capabilities()
    assert "ethereum-all" in caps["network_profiles"]


def test_cli_ethereum_plan_dry_run_returns_json():
    proc = subprocess.run(
        [sys.executable, "-m", "agilang", "chain", "ethereum-plan", "--mode", "archive"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["archive"] is True
    assert "execution" in payload["commands"]


def test_ethereum_stack_check_does_not_require_installed_clients_by_default():
    check = ethereum_stack_check(require_installed=False)
    assert check["ok"] is True
    assert check["checks"]["selected_clients_installed"] is True
