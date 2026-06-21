from agilang.zk import (
    zk_capabilities,
    zk_circuit,
    zk_commit,
    zk_verify_commitment,
    zk_merkle_proof,
    zk_verify_merkle_proof,
    zk_schnorr_keypair,
    zk_schnorr_prove,
    zk_schnorr_verify,
    zk_bridge_status,
    zk_nullifier,
)
from agilang.cli import main


def test_zk_circuit_commitment_merkle_and_schnorr():
    caps = zk_capabilities()
    assert caps["native_primitives"]["r1cs_constraints"] is True

    circuit = zk_circuit("square")
    circuit.var("x", 11, public=False)
    circuit.var("y", 121, public=True)
    circuit.assert_mul("x", "x", "y")
    assert circuit.check()["ok"] is True
    assert circuit.public_witness()["y"] == 121

    commitment = zk_commit({"amount": 100}, "salt")
    assert zk_verify_commitment(commitment, {"amount": 100}) is True
    assert zk_verify_commitment(commitment["commitment"], {"amount": 100}, "salt") is True

    proof = zk_merkle_proof(["alice", "bob", "carol"], 1)
    assert zk_verify_merkle_proof("bob", proof["index"], proof["proof"], proof["root"])

    key = zk_schnorr_keypair(12345)
    schnorr = zk_schnorr_prove(key["secret"], "hello")
    assert zk_schnorr_verify(schnorr, "hello") is True
    assert zk_schnorr_verify(schnorr, "tampered") is False

    assert zk_nullifier("secret", "scope") == zk_nullifier("secret", "scope")


def test_zk_bridge_status_and_cli(capsys):
    status = zk_bridge_status()
    assert "python_packages" in status
    assert "commands" in status

    for argv, needle in [
        (["zk", "capabilities"], "native_primitives"),
        (["zk", "circuit-demo", "--x", "8"], "public_witness"),
        (["zk", "merkle-demo"], "verified"),
        (["zk", "schnorr-demo", "--secret", "99"], "verified"),
    ]:
        try:
            main(argv)
        except SystemExit as exc:
            assert exc.code in (0, None)
        assert needle in capsys.readouterr().out


def test_zk_project_scaffold_runs(tmp_path):
    from agilang.scaffold import create_project
    from agilang.translator import AGILTranslator
    from agilang.cli import _execute_python

    result = create_project("Private Proof App", directory=tmp_path, template="zk")
    assert (result.root / "src/circuit.agi").exists()
    assert (result.root / "src/schnorr.agi").exists()
    code = AGILTranslator().translate_file(result.root / "src/main.agi")
    assert _execute_python(code, result.root / "src/main.agi") == 0
