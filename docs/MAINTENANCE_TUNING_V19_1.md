# AGILANG v1.9.1 Maintenance Tuning Runbook

This release fine-tunes the v1.9 blockchain framework and fixes the native runtime version mismatch reported by the hybrid-runtime tests.

## Native runtime alignment

The following now report `1.9.1` consistently:

- `agilang.__version__`
- `agilang.hybrid_runtime.RUNTIME_VERSION`
- `agi runtime status` / `agilang runtime status`
- `agi_net_runtime_version()` from the C runtime
- Linux x86_64 prebuilt runtime manifest

The Linux x86_64 runtime was rebuilt from `agilang/native/agilang_net_runtime.c`, and the manifest hashes were refreshed.

## Blockchain framework tuning

### Mempool

The mempool now rejects duplicate transaction hashes and validates negative values, negative nonces and negative gas prices. Higher-gas replacement for the same sender/nonce remains supported.

### Strict accounting

For private chains that need account-level validation, enable strict accounting:

```agi
let cfg = blockchain_config(
    validators={"alice": 100},
    genesis_state={"balances": {"alice": 1000, "bob": 0}},
    strict_accounting=True
)
```

With strict accounting enabled, the node rejects insufficient-balance transfers and can enforce sender nonce ordering.

### Canonical state replay

After importing blocks and applying fork choice, the node replays the canonical chain into state so balances, contracts and nonces remain deterministic after reorgs.

## Validation

```bash
python -m pytest tests/test_v19_blockchain.py tests/test_v19_maintenance_tuning.py -q
python -m pytest tests/test_v11_hybrid_runtime.py -q
python -m agilang test-examples
```

Expected result: all tests pass and `python -m agilang --version` prints `AGILANG 1.9.1`.

## Production boundary

This release improves correctness for private-chain/devnet usage. For public real-value deployments, add audited validator signatures, slashing, peer scoring, DoS controls, persistent peer discovery, state tries, pruning/snapshots, observability and independent consensus review.
