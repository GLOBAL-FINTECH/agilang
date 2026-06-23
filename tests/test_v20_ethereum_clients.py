from agilang.ethereum_clients import (
    default_ethereum_client_config,
    ethereum_client_capabilities,
    ethereum_stack_plan,
    ethereum_stack_check,
    load_ethereum_client_config,
    validate_ethereum_client_config,
    write_ethereum_client_config,
)


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


def test_ethereum_stack_check_does_not_require_installed_clients_by_default():
    check = ethereum_stack_check(require_installed=False)
    assert check["ok"] is True
    assert check["checks"]["selected_clients_installed"] is True
