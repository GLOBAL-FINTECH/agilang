from agilang.evm import (
    evm_capabilities,
    evm_bytecode_builder,
    evm_execute,
    evm_simulate_call,
    evm_estimate_gas,
    evm_trace,
    evm_abi_encode,
    evm_abi_decode,
    evm_contract_call_data,
    evm_world_state,
    evm_interpreter,
    evm_legacy_unsigned_tx,
)
from agilang.cli import main


def test_v18_evm_interpreter_arithmetic_storage_and_trace():
    code = evm_bytecode_builder().push(2).push(3).add().stop().hex()
    result = evm_execute(code, trace=True)
    assert result["ok"] is True
    assert result["stack"][-1] == 5
    assert result["gas_used"] > 0
    assert any(step["op"] == "ADD" for step in result["trace"])

    # PUSH1 0x2a PUSH0 SSTORE PUSH0 SLOAD STOP
    store_load = "0x602a5f555f5400"
    result = evm_simulate_call(store_load)
    assert result["ok"] is True
    assert result["stack"][-1] == 42
    assert result["storage"]["0"] == 42
    assert evm_estimate_gas(code) > 0
    assert evm_trace(code)[-1]["op"] == "STOP"


def test_v18_evm_return_memory_and_abi_dynamic():
    # Return uint256(42): PUSH1 2a PUSH0 MSTORE PUSH1 20 PUSH0 RETURN
    code = "0x602a5f5260205ff3"
    result = evm_execute(code)
    assert result["ok"] is True
    assert result["output"].endswith("2a")
    assert evm_abi_decode(["uint256"], result["output"])[0] == 42

    encoded = evm_abi_encode(["string", "uint256"], ["agilang", 7])
    decoded = evm_abi_decode(["string", "uint256"], encoded)
    assert decoded == ["agilang", 7]

    calldata = evm_contract_call_data("setMessage(string)", ["string"], ["hello"])
    assert calldata.startswith("0x") and len(calldata) > 10


def test_v18_world_state_call_and_unsigned_tx():
    world = evm_world_state()
    target = "0x00000000000000000000000000000000000000aa"
    caller = "0x00000000000000000000000000000000000000bb"
    world.create_account(target, code="0x602a5f5260205ff3")
    world.create_account(caller, balance=1000)
    interp = evm_interpreter(world)
    result = interp.execute(world.get_account(target).code, context={"address": target, "caller": caller, "origin": caller, "world": world})
    assert result.ok is True
    assert result.output.endswith("2a")

    tx = evm_legacy_unsigned_tx(1, 10, 21000, target, 5, "0x", 1)
    assert tx["rlp"].startswith("0x")
    assert tx["signing_hash"].startswith("0x")


def test_v18_evm_cli_commands(capsys):
    commands = [
        (["evm", "run", "0x600160020100"], "stack"),
        (["evm", "estimate-gas", "0x600160020100"], "9"),
        (["evm", "abi-decode", "uint256", "0x" + "0" * 63 + "a"], "10"),
        (["evm", "external-engine"], "available"),
    ]
    for argv, needle in commands:
        try:
            main(argv)
        except SystemExit as exc:
            assert exc.code in (0, None)
        assert needle in capsys.readouterr().out


def test_v18_evm_capabilities_not_stubbed():
    caps = evm_capabilities()
    assert caps["executable_interpreter"] is True
    assert caps["storage_model"] is True
    assert caps["call_simulation"] is True
    assert caps["supported_opcode_count"] >= 100
