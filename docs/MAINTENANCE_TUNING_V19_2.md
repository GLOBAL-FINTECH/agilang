# AGILANG v1.9.3 Strict Accounting Validation Runbook

This maintenance release hardens the v1.9 blockchain framework after the v1.9.1 tuning pass.

## What changed

- Block validation now re-executes transactions against the parent state.
- Imported blocks are rejected when receipts, gas used, state updates or state roots do not match deterministic execution.
- Canonical state replay now applies only successful transaction receipts.
- Failed transfers no longer mutate balances during reorg/state rebuild.
- Strict nonce ordering is enforced during block execution, not only at mempool admission.

## Validation

```bash
python -m pytest tests/test_v19_blockchain.py tests/test_v19_maintenance_tuning.py -q
python -m pytest tests/test_core.py tests/test_realtime.py tests/test_web.py tests/test_web_platform_v09.py -q
python -m pytest tests/test_v10_webrtc_security_react.py tests/test_v11_hybrid_runtime.py tests/test_v12_prebuilt_runtime.py tests/test_v13_scaffold_cross_platform.py -q
python -m pytest tests/test_v14_shared_hosting.py tests/test_v15_mobile_runtime.py tests/test_v16_systems_evm_network.py tests/test_v17_zero_knowledge.py tests/test_v18_production_evm.py -q
python -m agilang test-examples
```

Expected result: all tests pass and `python -m agilang --version` prints `AGILANG 1.9.3`.

## Production boundary

This improves private-chain/devnet correctness. Public real-value networks still need audited validator signatures, slashing, peer scoring, DoS controls, persistent peer discovery, state tries, pruning/snapshots, observability and independent consensus review.
