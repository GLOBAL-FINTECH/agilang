# AGILANG v2.1 Native SBQ Beacon + Ethereum PoS Runtime

> **Main runtime branch:** this branch is for the AGILANG language/runtime, CLI, blockchain runtime, native SBQ Beacon consensus, EVM/RPC tooling, Ethereum external-client orchestration, and runtime tests. The public web app starter remains on the `blog` branch.

AGILANG v2.1 adds a **native SBQ Beacon consensus layer** while preserving the v2.0.2 Ethereum PoS replica architecture.

It keeps three clean lanes:

1. **SBQ native chain runtime** — native SBQ Beacon consensus, AGILANG PoS/DPoS/dev consensus profiles, staking, validator penalty hooks, JSON-RPC, isolated validator API, archive profile, and configurable validator setup.
2. **Ethereum-style private fork/runtime mode** — Ethereum PoS replica architecture for private/custom networks.
3. **Ethereum mainnet connectivity** — orchestration of real external Ethereum execution, consensus, and validator clients for live Ethereum mainnet connectivity.

## Install locally

```bash
git clone https://github.com/GLOBAL-FINTECH/agilang.git
cd agilang
python -m pip install -e .
agi --version
```

Expected:

```text
AGILANG 2.1.0
```

## Create a blockchain project

```bash
agi new my chain --template blockchain
cd my-chain
agi run
agi run src/chain.agi
agi run src/beacon.agi
agi run src/staking.agi
agi run src/network.agi
agi run src/ethereum_clients.agi
agi run src/ethereum_consensus.agi
```

Generated blockchain projects now include:

```text
src/beacon.agi
src/ethereum_consensus.agi
config/beacon.json
config/ethereum-consensus-replica.json
config/ethereum-clients.json
config/network.json
config/rpc.json
storage/beacon.sqlite
docs/SBQ_BEACON_CHAIN_V21.md
docs/ETHEREUM_CONSENSUS_REPLICA_V20_2.md
docs/BLOCKCHAIN_RUNBOOK.md
```

## Native SBQ Beacon commands

```bash
agi beacon capabilities
agi beacon init
agi beacon status
agi beacon validators
agi beacon produce-block
agi beacon attest
agi beacon finalize
agi beacon fork-choice
agi beacon simulate --validators 64 --epochs 10
```

## Native SBQ Beacon features

- configurable slots
- configurable epochs
- validator registry
- weighted proposer selection
- beacon blocks
- execution payload bridge
- attestations
- checkpoint justification
- checkpoint finalization
- attestation-weighted fork choice
- double proposal detection
- double vote detection
- SQLite local/staging persistence
- simulation commands

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

Private Beacon API boundary:

```bash
agi chain ethereum-consensus-beacon --host 127.0.0.1 --port 5052
```

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
| SBQ native chain | Native SBQ Beacon or AGILANG PoS/DPoS/dev |
| Ethereum-derived private fork | Ethereum PoS replica by default |
| Ethereum mainnet connectivity | Real external Ethereum clients |
| Ethereum mainnet validation | Official Ethereum consensus/validator clients only |

## Documentation

- `docs/SBQ_BEACON_CHAIN_V21.md`
- `docs/ETHEREUM_CONSENSUS_REPLICA_V20_2.md`
- `docs/ETHEREUM_CLIENT_STACK_V20.md`
- `docs/SBQ_BLOCKCHAIN_NETWORK_STATUS.md`
- `docs/EVM_CHAIN_IMPLEMENTATIONS.md`
- `docs/JSON_RPC_METAMASK_V19_6.md`
- `docs/BLOCKCHAIN_FRAMEWORK_V19.md`

## Production boundary

This runtime is suitable for local development, staging, private-fork simulation, and AGILANG/SBQ chain implementation work. Before any public real-value launch, add independent security review, hardened networking, peer scoring, validator key isolation, validator penalty economics, DoS hardening, archive/indexer separation, long-running supervision, and production monitoring.

For Ethereum mainnet, AGILANG must rely on official Ethereum execution, consensus, and validator clients. Do not describe AGILANG custom consensus as an Ethereum mainnet validator.
