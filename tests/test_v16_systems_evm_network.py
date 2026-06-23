import json

from agilang.lowlevel_network import (
    lowlevel_network_capabilities,
    packet_json,
    packet_json_parse,
    udp_socket,
)
from agilang.evm import (
    evm_capabilities,
    evm_function_selector,
    evm_contract_call_data,
    evm_bytecode_builder,
    evm_disassemble,
)
from agilang.interop import systems_capabilities, python_package_status
from agilang.cli import main


def test_lowlevel_packet_and_udp_roundtrip():
    event = packet_json_parse(packet_json("systems.ready", {"ok": True}, "net"))
    assert event["type"] == "systems.ready"
    assert event["payload"]["ok"] is True

    sock = udp_socket("127.0.0.1", 0)
    try:
        addr = sock.address
        sock.send_to("hello", addr.host, addr.port)
        data, source = sock.recv_from(timeout=2.0)
        assert data == b"hello"
        assert source.port > 0
    finally:
        sock.close()

    assert lowlevel_network_capabilities()["tcp_server"] is True


def test_evm_selector_calldata_and_disassembler():
    selector = evm_function_selector("transfer(address,uint256)")
    assert selector.startswith("0x")
    assert len(selector) == 10
    calldata = evm_contract_call_data(
        "balanceOf(address)",
        ["address"],
        ["0x0000000000000000000000000000000000000001"],
    )
    assert calldata.startswith("0x")
    assert len(calldata) == 10 + 64
    code = evm_bytecode_builder().push(1).push(2).add().stop().hex()
    ops = evm_disassemble(code)
    assert [op["name"] for op in ops] == ["PUSH1", "PUSH1", "ADD", "STOP"]
    assert evm_capabilities()["json_rpc_client"] is True


def test_systems_capabilities_and_python_package_status():
    caps = systems_capabilities()
    assert caps["not_web_only"] is True
    assert caps["low_level_networking"]["udp_socket"] is True
    assert caps["evm"]["bytecode_builder"] is True
    status = python_package_status(["json", "package_that_should_not_exist_for_agilang_tests"])
    assert status["json"]["installed"] is True
    assert status["package_that_should_not_exist_for_agilang_tests"]["installed"] is False


def test_cli_v16_commands(capsys):
    for argv, needle in [
        (["net", "capabilities"], "udp_socket"),
        (["evm", "selector", "transfer(address,uint256)"], "0x"),
        (["systems", "capabilities"], "not_web_only"),
    ]:
        try:
            main(argv)
        except SystemExit as exc:
            assert exc.code in (0, None)
        output = capsys.readouterr().out
        assert needle in output


def test_systems_project_scaffold_runs(tmp_path):
    from agilang.scaffold import create_project
    from agilang.translator import AGILTranslator
    from agilang.cli import _execute_python

    result = create_project("Systems App", directory=tmp_path, template="systems")
    assert (result.root / "src/network.agi").exists()
    assert (result.root / "src/evm.agi").exists()
    source = result.root / "src/main.agi"
    code = AGILTranslator().translate_file(source)
    assert _execute_python(code, source) == 0
