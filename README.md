# AGILANG v1.9.3 Mainnet-Capable Blockchain Framework Edition

AGILANG v1.9.3 refines the v1.9 blockchain framework and expands the language beyond web, mobile, realtime, ZK and EVM tooling into a configurable **mainnet-capable blockchain framework**. It now supports selectable **PoS**, **DPoS/DPO**, and **Dev** consensus modes, stricter mainnet-style validation, validator block-signature hooks, peer/devnet sync, mempool management, fork choice, block production and a canonical chain database.

## Install locally

```bash
python -m pip install -e .
agi --version
```

Expected:

```text
AGILANG 1.9.3
```

For device and operating-system specific installation instructions, including Windows, macOS, Linux, Android, iOS/iPadOS, ChromeOS, Raspberry Pi, Docker, and shared hosting, see `DEVICE_OS_INSTALLATION.md`.

## Create a normal web app

```bash
agi new test app two
cd test-app-two
agi run
agi serve src/main.agi --host 127.0.0.1 --port 8000
```

## Create a blockchain app

```bash
agi new my chain --template blockchain
cd my-chain
agi run
agi run src/chain.agi
agi run src/mempool.agi
agi run src/devnet.agi
agi run src/evm_contract.agi
```

Generated blockchain projects include:

```text
src/main.agi
src/chain.agi
src/mempool.agi
src/devnet.agi
src/evm_contract.agi
config/validators.json
docs/BLOCKCHAIN_RUNBOOK.md
storage/.gitkeep
tests/test_main.agi
```


## v1.9.3 tuning highlights

- Fixed the native C runtime version mismatch so package, CLI diagnostics, source builds and prebuilt manifests report `1.9.3`.
- Rebuilt the Linux x86_64 native runtime artifacts and refreshed SHA-256 manifest hashes.
- Added pluggable consensus mode selection: `pos`, `dpos`/`dpo`, and `dev`.
- Added DPoS/DPO delegated producer selection using delegate lists and delegation weights.
- Added Dev consensus for deterministic local simulations.
- Added `blockchain_mainnet_config()` for strict accounting, nonce ordering, required block signatures, higher finality depth and non-zero minimum gas price.
- Added validator signature hooks and validation checks for signed blocks.
- Added `blockchain_consensus_simulation()` and `agi blockchain simulate-consensus`.
- Tightened mempool duplicate rejection and invalid transaction checks.
- Added optional strict-accounting mode for private chains that need balance and nonce validation during transaction admission and block execution.
- Added canonical state replay after fork-choice updates so balances, contracts and nonces remain deterministic after reorgs.
- Re-executes imported blocks against parent state and rejects forged receipts, state updates and state roots.
- Added regression tests covering runtime alignment, duplicate rejection, strict-accounting state rebuilds and imported-block validation hardening.

## Blockchain CLI

```bash
agi blockchain capabilities
agi blockchain demo
agi blockchain simulate-consensus
agi blockchain init-genesis --db storage/chain.sqlite --validator alice:60 --validator bob:40
agi blockchain init-genesis --consensus dpo --validator alice:60 --validator bob:40
agi blockchain mempool-demo --consensus pos --sender alice --to bob --value 10
agi blockchain produce-block --consensus dev --validator alice --to bob --value 10
agi blockchain devnet --consensus dpos --blocks 3
agi blockchain merkle-root alice,bob,carol
```

## Blockchain standard-library functions

```agi
blockchain_capabilities()
blockchain_config()
blockchain_mainnet_config()
blockchain_transaction()
blockchain_merkle_root()
consensus_engine()
pos_consensus_engine()
dpos_consensus_engine()
dev_consensus_engine()
blockchain_node()
blockchain_devnet()
blockchain_consensus_simulation()
blockchain_demo()
```

## Included blockchain components

| Component | Status |
|---|---:|
| Proof-of-Stake consensus engine | Included |
| DPoS/DPO consensus engine | Included |
| Dev consensus engine | Included |
| Pluggable consensus selector | Included |
| Weighted validator proposer selection | Included |
| Delegated producer selection | Included |
| Mainnet profile config | Included |
| Validator block-signature hooks | Included |
| Block validation | Included |
| Block production | Included |
| Mempool validation/replacement/ordering | Included |
| Canonical SQLite chain database | Included |
| Fork-choice scoring | Included |
| Finality-depth marking | Included |
| In-process p2p/devnet sync | Included |
| Transaction/block gossip hooks | Included |
| EVM execution hooks | Included |

## Existing AGILANG platform layers preserved

AGILANG still includes the previous framework layers:

- web apps and APIs
- React/React Native scaffolding
- WebSocket realtime transport
- WebRTC signaling helpers
- CGI/FastCGI shared-hosting deployment
- native C + Python hybrid runtime bridge
- low-level TCP/UDP networking
- executable EVM runtime toolkit
- zero-knowledge developer primitives
- package manager, parser, AST, checker, formatter, LSP and CI/CD workflows

## Production boundary

AGILANG v1.9.3 is a mainnet-capable framework for simulation, staging, private chains and custom chain development. It includes a stricter mainnet profile and signature-validation hooks, but it is still not a finished public real-value mainnet client. Before public launch, add audited cryptographic networking/signatures, persistent peer discovery, peer scoring, slashing economics, DoS protection, state tries, pruning, snapshots, monitoring, formal consensus review and independent security audits.

See `docs/BLOCKCHAIN_FRAMEWORK_V19.md` and `docs/MAINTENANCE_TUNING_V19_1.md and docs/MAINTENANCE_TUNING_V19_2.md` for the full runbook.
