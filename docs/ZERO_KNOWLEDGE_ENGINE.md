# AGILANG v1.7 Zero-Knowledge Engine

AGILANG v1.7 adds a zero-knowledge systems layer so the language is not limited to web apps. The ZK layer is designed as a practical bridge between AGILANG syntax and production cryptographic toolchains.

## What is included natively

AGILANG ships dependency-light primitives that work immediately:

- finite-field arithmetic through `zk_field()`
- R1CS-style circuit construction through `zk_circuit()`
- witness checking for constraints
- salted hash commitments through `zk_commit()`
- Merkle tree membership proofs through `zk_merkle_tree()` and `zk_merkle_proof()`
- nullifier generation through `zk_nullifier()`
- Schnorr-style Fiat-Shamir proof demos through `zk_schnorr_prove()`
- external prover/verifier bridge detection through `zk_bridge_status()`

These are excellent for development, protocol prototyping, education, and integration tests.

## Important production boundary

The native v1.7 ZK module is **not** an audited production SNARK/STARK prover. Production proving should be backed by proven external engines or precompiled native packages, for example:

- Circom/snarkjs
- Halo2
- Noir/Nargo
- RISC Zero
- SP1
- arkworks
- gnark

AGILANG provides the clean application-level interface and package bridge.

## CLI commands

```bash
agi zk capabilities
agi zk bridge-status
agi zk demo
agi zk circuit-demo --x 7
agi zk merkle-demo --leaves alice,bob,carol --index 1
agi zk schnorr-demo --secret 12345 --message agilang
agi zk commit "private-value" --salt demo-salt
agi zk verify-commit <commitment> "private-value" --salt demo-salt
```

## AGILANG example

```agi
fn main() -> i32:
    let circuit = zk_circuit("square_demo")
    circuit.var("secret", 9, public=False)
    circuit.var("square", 81, public=True)
    circuit.assert_mul("secret", "secret", "square")
    print(circuit.check())

    let commitment = zk_commit({"balance": 100}, "salt")
    print(zk_verify_commitment(commitment, {"balance": 100}))

    let proof = zk_merkle_proof(["alice", "bob", "carol"], 1)
    print(zk_verify_merkle_proof("bob", proof["index"], proof["proof"], proof["root"]))
    return 0
```

## ZK app starter

Create a starter project:

```bash
agi new private proof app --template zk
cd private-proof-app
agi run
agi run src/circuit.agi
agi run src/schnorr.agi
```

## Recommended architecture for real ZK products

```text
AGILANG syntax
  ↓
ZK standard-library API
  ↓
R1CS/commitment/Merkle/nullifier app model
  ↓
External prover/verifier bridge or precompiled native prover
  ↓
EVM verifier contract / blockchain / backend API
```

This architecture lets AGILANG stay flexible while using serious cryptographic engines where correctness and auditing matter.
