# Changelog

## v1.9.3 - Mainnet-Capable Consensus Framework

- Added pluggable blockchain consensus selection with `consensus_mode="pos"`, `"dpos"`/`"dpo"`, and `"dev"`.
- Added DPoS/DPO producer selection using delegate lists and delegation-weight maps.
- Added developer consensus mode for fast deterministic local simulation.
- Added a stricter `blockchain_mainnet_config()` profile that enables strict accounting, nonce ordering, required block signatures, non-zero gas price and higher finality depth.
- Added validator block-signature hooks with deterministic HMAC-backed local simulation keys.
- Added validator-signature verification during block validation and signature tamper regression tests.
- Added `blockchain_consensus_simulation()` and `agi blockchain simulate-consensus` covering PoS, DPoS/DPO, Dev consensus and signed mainnet-profile blocks.
- Updated CLI options to accept `--consensus pos|dpos|dpo|dev` for genesis, mempool, block-production and devnet flows.
- Updated package/runtime/native metadata to `1.9.3` and rebuilt Linux x86_64 native prebuilt artifacts.

## v1.9.2 - Strict Accounting Block Validation Hardening

- Recomputed block execution during validation against the parent state.
- Rejected imported blocks with forged receipts, forged state updates or invalid state roots.
- Made canonical replay apply only transactions with successful receipts so failed transfers cannot mutate balances.
- Added strict-accounting nonce validation during block execution, not only mempool submission.
- Added regression coverage for malicious imported blocks that try to push balances negative.

## v1.9.1 - Blockchain Framework Maintenance + Runtime Alignment

- Fixed native C runtime version alignment: package version, `agilang.hybrid_runtime.RUNTIME_VERSION`, C source metadata, runtime diagnostics and Linux prebuilt manifests now report `1.9.1`.
- Rebuilt Linux x86_64 precompiled runtime artifacts and refreshed SHA-256 checksums.
- Tightened mempool admission by rejecting duplicate transaction hashes instead of silently re-accepting them.
- Added invalid negative value/nonce/gas-price checks.
- Added optional `strict_accounting` and `enforce_nonce_order` configuration flags for balance and nonce validation.
- Added canonical state replay after fork-choice updates/reorgs to keep balances, contracts and nonces deterministic.
- Added gas-used validation for imported blocks.
- Added focused regression coverage for runtime version alignment, duplicate rejection and strict-accounting state rebuilds.

## v1.9.0 - Full Blockchain Framework Edition

- Added `agilang.blockchain` module.
- Added configurable Proof-of-Stake consensus engine with weighted validator proposer selection.
- Added transaction/mempool management with validation, replacement, gas-price ordering and capacity limits.
- Added block production, block validation, receipts, state roots, transaction roots and gas limits.
- Added persistent SQLite canonical chain database for blocks, transactions, metadata and state.
- Added stake-weighted-height fork choice and finality-depth marking.
- Added in-process p2p/devnet sync with transaction and block gossip helpers.
- Added EVM execution hooks for contract calls/deployments through the v1.8 EVM runtime.
- Added `agi blockchain` CLI group: capabilities, demo, init-genesis, mempool-demo, produce-block, devnet, merkle-root.
- Added `--template blockchain` scaffold with `src/chain.agi`, `src/mempool.agi`, `src/devnet.agi`, `src/evm_contract.agi`, validator config and blockchain runbook.
- Added `examples/blockchain_full_node.agi`, `docs/BLOCKCHAIN_FRAMEWORK_V19.md` and v1.9 tests.
## v1.8.0 - Production EVM Runtime Edition

- Upgraded EVM support from helper-only tooling to an executable EVM runtime toolkit.
- Added bytecode interpreter with stack, memory, storage, world-state accounts, logs, traces and gas accounting.
- Added local call simulation, CREATE/CREATE2 simulation, CALL/DELEGATECALL/STATICCALL handling, return/revert handling and storage updates.
- Added richer ABI encoding/decoding for static and common dynamic types.
- Added RLP unsigned transaction tooling and external audited-engine bridge detection.
- Added CLI commands: `evm run`, `evm trace`, `evm estimate-gas`, `evm abi-decode`, `evm unsigned-tx`, and `evm external-engine`.
- Added `examples/evm_production_runtime.agi` and `docs/EVM_PRODUCTION_RUNTIME_V18.md`.

## v1.7.0 - Zero-Knowledge Systems Edition

AGILANG v1.7 expands the v1.6 general systems/EVM platform with a zero-knowledge systems layer.

### Added

- `agilang.zk` module
- finite-field helper: `zk_field()`
- R1CS-style circuit builder: `zk_circuit()`
- witness/constraint checking
- salted hash commitments: `zk_commit()` and `zk_verify_commitment()`
- Merkle membership proofs: `zk_merkle_tree()`, `zk_merkle_proof()`, `zk_verify_merkle_proof()`
- nullifier helper: `zk_nullifier()`
- Schnorr-style Fiat-Shamir proof demo helpers
- external ZK engine bridge: `zk_external_engine()` and `zk_bridge_status()`
- `agi zk` CLI group
- `--template zk` project scaffold
- `examples/zero_knowledge_demo.agi`
- `docs/ZERO_KNOWLEDGE_ENGINE.md`
- v1.7 tests

### Updated

- package version to `1.7.0`
- native C runtime metadata to `1.7.0`
- Linux x86_64 prebuilt native runtime rebuilt with v1.7 metadata
- systems capability report now includes zero-knowledge support

### Production boundary

The built-in ZK primitives are developer/protocol-building primitives. AGILANG does not claim to include an audited production SNARK/STARK prover yet. For production proving, use an external engine or a precompiled native prover package through AGILANG's interop layer.
