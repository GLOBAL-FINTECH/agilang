# AGILANG v2.0.2 Ethereum PoS  Consensus Runtime

> **Main runtime branch:** this branch is for the AGILANG language/runtime, CLI, blockchain runtime, EVM/RPC tooling, and runtime tests. The public web app starter remains on the `blog` branch.

AGILANG v2.0.2 is a blockchain/runtime upgrade that makes Ethereum-derived fork mode follow an **Ethereum proof-of-stake  design by default** instead of using a separate AGILANG consensus system.

It keeps two clean lanes:

1. **SBQ / AGILANG custom-chain runtime** — native PoS/DPoS/dev consensus, staking, slashing hooks, JSON-RPC, isolated validator API and archive profile.
2. **Ethereum-style fork/runtime mode** — Ethereum PoS replica architecture for private/custom networks, plus real external Ethereum clients for live Ethereum mainnet connectivity.

## Install locally

```bash
git clone https://github.com/GLOBAL-FINTECH/agilang.git
cd agilang
python -m pip install -e .
agi --version
```

Expected:

```text
AGILANG 2.0.2
```

## Create a blockchain project

```bash
agi new my chain --template blockchain
cd my-chain
agi run
agi run src/chain.agi
agi run src/staking.agi
agi run src/network.agi
agi run src/ethereum_clients.agi
agi run src/ethereum_consensus.agi
```

Generated blockchain projects now include:

```text
src/ethereum_consensus.agi
config/ethereum-consensus-replica.json
config/ethereum-clients.json
config/network.json
config/rpc.json
docs/ETHEREUM_CONSENSUS_REPLICA_V20_2.md
docs/BLOCKCHAIN_RUNBOOK.md
```

## Ethereum PoS replica commands

```bash
agi chain ethereum-consensus-capabilities
agi chain consensus-replacement-plan --network private-fork --consensus ethereum-pos-replica --chain-id 901900
agi chain ethereum-consensus-write-config --chain-id 901900
agi chain ethereum-consensus-check
agi chain ethereum-consensus-sim
agi chain plan --mode ethereum-consensus-replica
agi chain start --mode ethereum-consensus-replica --config config/network.json
```

Private Beacon API:

```bash
agi chain ethereum-consensus-beacon --host 127.0.0.1 --port 5052
```

## What the replica models

- execution/consensus split
- private Engine API boundary
- private Beacon API service
- 12-second slots
- 32-slot epochs
- validator registry
- proposer duties
- attestation committees
- source/target/head votes
- LMD-GHOST-style head choice
- Casper FFG-style finality
- reward/penalty hooks
- slashing hooks
- private validator API isolation

## Ethereum mainnet mode

Live Ethereum mainnet remains external-client based:

```bash
agi chain ethereum-plan --mode full
agi chain ethereum-plan --mode archive
agi chain ethereum-plan --mode validator --fee-recipient 0x0000000000000000000000000000000000000000
agi chain ethereum-start --mode full --dry-run
```

AGILANG does not override live Ethereum mainnet consensus. The replica profile is for private/custom Ethereum-derived networks with a new chain ID and custom genesis.

## Correct architecture

| Mode | Consensus |
|---|---|
| SBQ native chain | AGILANG PoS/DPoS/dev |
| Ethereum-derived private fork | Ethereum PoS replica by default |
| Ethereum mainnet connectivity | Real external Ethereum clients |
| Ethereum mainnet validation | Official Ethereum consensus/validator clients only |

## Documentation

- `docs/ETHEREUM_CONSENSUS_REPLICA_V20_2.md`
- `docs/ETHEREUM_CLIENT_STACK_V20.md`
- `docs/SBQ_BLOCKCHAIN_NETWORK_STATUS.md`
- `docs/EVM_CHAIN_IMPLEMENTATIONS.md`
- `docs/JSON_RPC_METAMASK_V19_6.md`
- `docs/BLOCKCHAIN_FRAMEWORK_V19.md`

## Validation summary

Grouped validation from the uploaded AGILANG v2.0.2 runtime package:

```text
Blockchain/RPC/staking/network/Ethereum consensus: 67 passed
Core/web/realtime/security: 31 passed
Runtime/prebuilt/scaffold: 13 passed
Shared-hosting/mobile/systems/EVM/ZK: 22 passed
Total: 133 passed
```

Examples:

```text
27 examples passed
2 network/long-running examples skipped by default
```

Local connector validation of the uploaded package confirmed the Ethereum consensus/client group:

```text
tests/test_v202_ethereum_consensus_replica.py
tests/test_v201_agilang_consensus_replacement.py
tests/test_v20_ethereum_clients.py
28 passed
```

## Production boundary

This runtime is suitable for local development, staging, private-fork simulation, and AGILANG/SBQ chain implementation work. Before any public real-value launch, add independent security review, hardened networking, peer scoring, validator key isolation, slashing economics, DoS hardening, archive/indexer separation, and production monitoring.

For Ethereum mainnet, AGILANG must rely on official Ethereum execution, consensus, and validator clients. Do not describe AGILANG custom consensus as an Ethereum mainnet validator.
