"""AGILANG v1.7 zero-knowledge systems primitives.

This module gives AGILANG a practical ZK-facing API without pretending that a
small standard-library module is a full audited SNARK/STARK prover.  It includes
safe deterministic developer primitives that are useful for building and testing
ZK applications:

* R1CS-style constraint systems and witness checks.
* Hash commitments.
* Merkle tree membership proofs.
* A Schnorr-style non-interactive proof-of-knowledge demo.
* External prover/verifier bridge descriptors for production engines.

Production SNARK/STARK proving should still be backed by audited engines such as
Circom/snarkjs, Halo2, Noir, RISC Zero, SP1, arkworks, gnark, or a dedicated
precompiled native library.  AGILANG owns the syntax, glue layer, validation,
and capability interface.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import secrets
import shutil
import subprocess
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

ZK_VERSION = "1.7.0"
BN254_SCALAR_FIELD = 21888242871839275222246405745257275088548364400416034343698204186575808495617
DEV_SCHNORR_MODULUS = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
DEV_SCHNORR_GENERATOR = 5


def _jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bytes):
        return "0x" + value.hex()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return str(value)


def _canonical_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _to_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, str):
        s = value.strip()
        if s.startswith(("0x", "0X")) and len(s) % 2 == 0:
            try:
                return bytes.fromhex(s[2:])
            except ValueError:
                pass
        return value.encode("utf-8")
    return _canonical_json(value).encode("utf-8")


def _hex_digest(*parts: Any, domain: str = "AGILANG-ZK") -> str:
    h = hashlib.sha256(domain.encode("utf-8"))
    for part in parts:
        raw = _to_bytes(part)
        h.update(len(raw).to_bytes(8, "big"))
        h.update(raw)
    return "0x" + h.hexdigest()


def _hash_int(*parts: Any, modulus: int = BN254_SCALAR_FIELD, domain: str = "AGILANG-ZK-INT") -> int:
    return int(_hex_digest(*parts, domain=domain)[2:], 16) % int(modulus)


class ZKField:
    """Small finite-field helper for constraint arithmetic."""

    def __init__(self, modulus: int = BN254_SCALAR_FIELD, name: str = "bn254") -> None:
        if int(modulus) <= 2:
            raise ValueError("field modulus must be greater than 2")
        self.modulus = int(modulus)
        self.name = name

    def normalize(self, value: int) -> int:
        return int(value) % self.modulus

    def add(self, a: int, b: int) -> int:
        return (int(a) + int(b)) % self.modulus

    def sub(self, a: int, b: int) -> int:
        return (int(a) - int(b)) % self.modulus

    def mul(self, a: int, b: int) -> int:
        return (int(a) * int(b)) % self.modulus

    def neg(self, a: int) -> int:
        return (-int(a)) % self.modulus

    def inv(self, a: int) -> int:
        a = int(a) % self.modulus
        if a == 0:
            raise ZeroDivisionError("cannot invert zero in a finite field")
        return pow(a, -1, self.modulus)

    def div(self, a: int, b: int) -> int:
        return self.mul(a, self.inv(b))

    def hash_to_field(self, value: Any) -> int:
        return _hash_int(value, modulus=self.modulus, domain=f"AGILANG-ZK-FIELD:{self.name}")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "modulus": self.modulus}


def zk_field(name: str = "bn254", modulus: int | None = None) -> ZKField:
    if modulus is not None:
        return ZKField(int(modulus), name=name)
    if name.lower() in {"bn254", "alt_bn128", "babyjubjub"}:
        return ZKField(BN254_SCALAR_FIELD, name="bn254")
    if name.lower() in {"dev", "secp-dev"}:
        return ZKField(DEV_SCHNORR_MODULUS, name="dev")
    raise ValueError(f"unknown field preset: {name}")


@dataclass
class ZKConstraint:
    kind: str
    terms: tuple[str, ...]
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "terms": list(self.terms), "note": self.note}


@dataclass
class ZKCircuit:
    name: str = "circuit"
    field: ZKField = dc_field(default_factory=zk_field)
    variables: dict[str, int | None] = dc_field(default_factory=dict)
    public_inputs: set[str] = dc_field(default_factory=set)
    private_inputs: set[str] = dc_field(default_factory=set)
    constraints: list[ZKConstraint] = dc_field(default_factory=list)

    def var(self, name: str, value: int | None = None, *, public: bool = False) -> str:
        if not name or not isinstance(name, str):
            raise ValueError("variable name must be a non-empty string")
        self.variables[name] = None if value is None else self.field.normalize(int(value))
        if public:
            self.public_inputs.add(name)
            self.private_inputs.discard(name)
        else:
            self.private_inputs.add(name)
            self.public_inputs.discard(name)
        return name

    def set(self, name: str, value: int) -> "ZKCircuit":
        if name not in self.variables:
            self.var(name)
        self.variables[name] = self.field.normalize(int(value))
        return self

    def assert_equal(self, left: str, right: str, note: str = "") -> "ZKCircuit":
        self.constraints.append(ZKConstraint("eq", (left, right), note))
        return self

    def assert_add(self, left: str, right: str, out: str, note: str = "") -> "ZKCircuit":
        self.constraints.append(ZKConstraint("add", (left, right, out), note))
        return self

    def assert_mul(self, left: str, right: str, out: str, note: str = "") -> "ZKCircuit":
        self.constraints.append(ZKConstraint("mul", (left, right, out), note))
        return self

    def _value(self, name: str, witness: dict[str, Any] | None = None) -> int:
        if witness and name in witness:
            return self.field.normalize(int(witness[name]))
        if name not in self.variables:
            raise KeyError(f"unknown circuit variable: {name}")
        value = self.variables[name]
        if value is None:
            raise ValueError(f"missing witness value for variable: {name}")
        return self.field.normalize(int(value))

    def check(self, witness: dict[str, Any] | None = None) -> dict[str, Any]:
        failures: list[dict[str, Any]] = []
        for idx, constraint in enumerate(self.constraints):
            try:
                terms = constraint.terms
                if constraint.kind == "eq":
                    ok = self._value(terms[0], witness) == self._value(terms[1], witness)
                elif constraint.kind == "add":
                    ok = self.field.add(self._value(terms[0], witness), self._value(terms[1], witness)) == self._value(terms[2], witness)
                elif constraint.kind == "mul":
                    ok = self.field.mul(self._value(terms[0], witness), self._value(terms[1], witness)) == self._value(terms[2], witness)
                else:
                    ok = False
                    raise ValueError(f"unknown constraint kind: {constraint.kind}")
                if not ok:
                    failures.append({"index": idx, "constraint": constraint.to_dict(), "error": "constraint not satisfied"})
            except Exception as exc:  # keep diagnostics useful for CLI/tests
                failures.append({"index": idx, "constraint": constraint.to_dict(), "error": str(exc)})
        return {"ok": not failures, "failures": failures, "constraints": len(self.constraints)}

    def public_witness(self, witness: dict[str, Any] | None = None) -> dict[str, int]:
        return {name: self._value(name, witness) for name in sorted(self.public_inputs)}

    def private_witness(self, witness: dict[str, Any] | None = None) -> dict[str, int]:
        return {name: self._value(name, witness) for name in sorted(self.private_inputs)}

    def to_r1cs_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "field": self.field.to_dict(),
            "variables": sorted(self.variables.keys()),
            "public_inputs": sorted(self.public_inputs),
            "private_inputs": sorted(self.private_inputs),
            "constraints": [c.to_dict() for c in self.constraints],
        }


def zk_circuit(name: str = "circuit", field_name: str = "bn254") -> ZKCircuit:
    return ZKCircuit(name=name, field=zk_field(field_name))


def zk_commit(value: Any, salt: str | None = None) -> dict[str, Any]:
    salt = salt or secrets.token_hex(32)
    commitment = _hex_digest(value, salt, domain="AGILANG-ZK-COMMIT-v1")
    return {"scheme": "sha256_commitment", "commitment": commitment, "salt": salt}


def zk_verify_commitment(commitment: str | dict[str, Any], value: Any, salt: str | None = None) -> bool:
    if isinstance(commitment, dict):
        salt = str(commitment.get("salt"))
        commitment = str(commitment.get("commitment"))
    if salt is None:
        raise ValueError("salt is required to verify a hash commitment")
    return str(commitment).lower() == zk_commit(value, salt)["commitment"].lower()


class ZKMerkleTree:
    def __init__(self, leaves: Sequence[Any]) -> None:
        if not leaves:
            raise ValueError("Merkle tree requires at least one leaf")
        self.leaves = list(leaves)
        level = [self.leaf_hash(leaf) for leaf in self.leaves]
        self.levels: list[list[str]] = [level]
        while len(level) > 1:
            nxt: list[str] = []
            for i in range(0, len(level), 2):
                left = level[i]
                right = level[i + 1] if i + 1 < len(level) else left
                nxt.append(self.node_hash(left, right))
            level = nxt
            self.levels.append(level)

    @staticmethod
    def leaf_hash(leaf: Any) -> str:
        return _hex_digest(leaf, domain="AGILANG-ZK-MERKLE-LEAF-v1")

    @staticmethod
    def node_hash(left: str, right: str) -> str:
        return _hex_digest(left, right, domain="AGILANG-ZK-MERKLE-NODE-v1")

    @property
    def root(self) -> str:
        return self.levels[-1][0]

    def proof(self, index: int) -> list[dict[str, str]]:
        if index < 0 or index >= len(self.leaves):
            raise IndexError("leaf index out of range")
        proof: list[dict[str, str]] = []
        idx = index
        for level in self.levels[:-1]:
            sibling_idx = idx ^ 1
            if sibling_idx >= len(level):
                sibling_idx = idx
            position = "left" if sibling_idx < idx else "right"
            proof.append({"position": position, "hash": level[sibling_idx]})
            idx //= 2
        return proof

    @classmethod
    def verify(cls, leaf: Any, index: int, proof: Sequence[dict[str, str]], root: str) -> bool:
        current = cls.leaf_hash(leaf)
        idx = index
        for step in proof:
            sibling = step["hash"]
            if step.get("position") == "left":
                current = cls.node_hash(sibling, current)
            else:
                current = cls.node_hash(current, sibling)
            idx //= 2
        return current.lower() == str(root).lower()

    def to_dict(self) -> dict[str, Any]:
        return {"root": self.root, "leaves": len(self.leaves), "levels": len(self.levels)}


def zk_merkle_tree(leaves: Sequence[Any]) -> ZKMerkleTree:
    return ZKMerkleTree(leaves)


def zk_merkle_proof(leaves: Sequence[Any], index: int) -> dict[str, Any]:
    tree = ZKMerkleTree(leaves)
    return {"root": tree.root, "index": index, "leaf": leaves[index], "proof": tree.proof(index)}


def zk_verify_merkle_proof(leaf: Any, index: int, proof: Sequence[dict[str, str]], root: str) -> bool:
    return ZKMerkleTree.verify(leaf, index, proof, root)


def zk_nullifier(secret: Any, scope: str = "default") -> str:
    return _hex_digest(secret, scope, domain="AGILANG-ZK-NULLIFIER-v1")


def zk_schnorr_keypair(secret: int | None = None, *, generator: int = DEV_SCHNORR_GENERATOR, modulus: int = DEV_SCHNORR_MODULUS) -> dict[str, int]:
    order = int(modulus) - 1
    if secret is None:
        secret = secrets.randbelow(order - 1) + 1
    secret = int(secret) % order
    if secret == 0:
        secret = 1
    public = pow(int(generator), secret, int(modulus))
    return {"secret": secret, "public": public, "generator": int(generator), "modulus": int(modulus)}


def zk_schnorr_prove(secret: int, message: Any = "", *, nonce: int | None = None, generator: int = DEV_SCHNORR_GENERATOR, modulus: int = DEV_SCHNORR_MODULUS) -> dict[str, Any]:
    modulus = int(modulus)
    generator = int(generator)
    order = modulus - 1
    secret = int(secret) % order
    nonce = int(nonce) % order if nonce is not None else secrets.randbelow(order - 1) + 1
    public = pow(generator, secret, modulus)
    commitment = pow(generator, nonce, modulus)
    challenge = _hash_int(generator, modulus, public, commitment, message, modulus=order, domain="AGILANG-ZK-SCHNORR-FS-v1")
    response = (nonce + challenge * secret) % order
    return {
        "scheme": "schnorr_fiat_shamir_dev",
        "public": public,
        "commitment": commitment,
        "challenge": challenge,
        "response": response,
        "message": _jsonable(message),
        "generator": generator,
        "modulus": modulus,
    }


def zk_schnorr_verify(proof: dict[str, Any], message: Any = None) -> bool:
    generator = int(proof["generator"])
    modulus = int(proof["modulus"])
    order = modulus - 1
    public = int(proof["public"])
    commitment = int(proof["commitment"])
    response = int(proof["response"])
    msg = proof.get("message", "") if message is None else message
    challenge = _hash_int(generator, modulus, public, commitment, msg, modulus=order, domain="AGILANG-ZK-SCHNORR-FS-v1")
    if int(proof.get("challenge", challenge)) != challenge:
        return False
    left = pow(generator, response, modulus)
    right = (commitment * pow(public, challenge, modulus)) % modulus
    return left == right


def zk_range_constraints(circuit: ZKCircuit, value_name: str, bit_names: Sequence[str], *, out_name: str | None = None) -> ZKCircuit:
    """Add bitness constraints that reconstruct a value from binary witness bits.

    This is a constraint builder, not a full range-proof prover.  It is useful
    for generating a circuit that a production SNARK/STARK backend can prove.
    """
    total_name = out_name or f"{value_name}_bits_total"
    if total_name not in circuit.variables:
        circuit.var(total_name, None, public=False)
    for bit in bit_names:
        # b * b = b proves b is 0 or 1 over the field.
        circuit.assert_mul(bit, bit, bit, note="bitness")
    # Full linear combination constraints need linear R1CS support; keep the
    # intended reconstruction formula in the exported circuit metadata.
    circuit.constraints.append(ZKConstraint("range_bits", tuple([value_name, total_name, *bit_names]), "value equals binary decomposition"))
    return circuit


def zk_bridge_status() -> dict[str, Any]:
    packages = ["Crypto", "py_ecc", "web3", "eth_abi"]
    commands = ["snarkjs", "circom", "nargo", "halo2", "risc0", "cargo"]
    return {
        "python_packages": {name: importlib.util.find_spec(name) is not None for name in packages},
        "commands": {name: shutil.which(name) is not None for name in commands},
        "recommended_external_engines": ["circom/snarkjs", "halo2", "noir/nargo", "risc0", "sp1", "arkworks", "gnark"],
    }


def zk_external_engine(name: str, *, command: str | None = None, workdir: str | Path | None = None) -> "ZKExternalEngine":
    return ZKExternalEngine(name=name, command=command or name, workdir=Path(workdir) if workdir else None)


@dataclass
class ZKExternalEngine:
    name: str
    command: str
    workdir: Path | None = None

    def available(self) -> bool:
        return shutil.which(self.command) is not None

    def run(self, args: Sequence[str], *, timeout: float = 120.0) -> dict[str, Any]:
        if not self.available():
            raise RuntimeError(f"external ZK engine command not found: {self.command}")
        completed = subprocess.run([self.command, *args], cwd=str(self.workdir) if self.workdir else None, text=True, capture_output=True, timeout=timeout, check=False)
        return {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "command": self.command, "available": self.available(), "workdir": str(self.workdir) if self.workdir else None}


def zk_capabilities() -> dict[str, Any]:
    bridge = zk_bridge_status()
    return {
        "version": ZK_VERSION,
        "native_primitives": {
            "field_arithmetic": True,
            "r1cs_constraints": True,
            "witness_checker": True,
            "hash_commitments": True,
            "merkle_membership_proofs": True,
            "schnorr_fiat_shamir_demo": True,
            "nullifiers": True,
        },
        "external_engine_bridge": True,
        "supported_external_engines": bridge["recommended_external_engines"],
        "production_snark_prover_builtin": False,
        "production_stark_prover_builtin": False,
        "notes": [
            "AGILANG v1.7 includes developer ZK primitives and bridge hooks.",
            "Use audited external SNARK/STARK engines or native libraries for production proving.",
        ],
    }


def zk_demo_payload() -> dict[str, Any]:
    circuit = zk_circuit("square_demo")
    circuit.var("x", 7, public=False)
    circuit.var("y", 49, public=True)
    circuit.assert_mul("x", "x", "y", note="prove private x squares to public y")
    merkle = zk_merkle_tree(["alice", "bob", "carol"])
    proof = merkle.proof(1)
    keys = zk_schnorr_keypair(12345)
    schnorr = zk_schnorr_prove(keys["secret"], "agilang")
    return {
        "capabilities": zk_capabilities(),
        "circuit_check": circuit.check(),
        "public_witness": circuit.public_witness(),
        "commitment": zk_commit({"balance": 100}, "demo-salt"),
        "merkle_root": merkle.root,
        "merkle_verified": zk_verify_merkle_proof("bob", 1, proof, merkle.root),
        "schnorr_verified": zk_schnorr_verify(schnorr, "agilang"),
    }
