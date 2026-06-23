# AGILANG v2.0.2 Ethereum PoS Replica Consensus Fork

AGILANG v2.0.2 changes the default Ethereum-derived fork design from a separate AGILANG consensus engine to an **Ethereum proof-of-stake replica profile**.

This profile is for private/custom Ethereum-derived networks. Live Ethereum mainnet still requires official Ethereum execution, consensus and validator clients.

## Default fork consensus

```bash
agi chain consensus-replacement-plan --network private-fork --consensus ethereum-pos-replica --chain-id 901900
agi chain ethereum-consensus-check
agi chain ethereum-consensus-sim
```

## Design primitives

The replica profile models:

- execution/consensus split
- private Engine API boundary
- Beacon API service profile
- 12-second slots
- 32-slot epochs
- validator registry
- proposer duties
- attestation committees
- source / target / head votes
- LMD-GHOST-style head choice
- Casper FFG-style justification/finalization
- reward / penalty hooks
- slashing hooks
- private validator API

## Network mode

```bash
agi chain plan --mode ethereum-consensus-replica
agi chain start --mode ethereum-consensus-replica --config config/network.json
```

Default ports:

| Service | Host | Port | Purpose |
|---|---:|---:|---|
| Public JSON-RPC | 127.0.0.1 | 8545 | Wallet/app RPC |
| Private Beacon API | 127.0.0.1 | 5052 | Consensus replica status/finality |
| Private validator API | 127.0.0.1 | 8651 | Validator/admin duties |
| P2P profile | 0.0.0.0 | 30333 | Node sync/gossip profile |
| Metrics | 127.0.0.1 | 9100 | Ops/health |

## Public Ethereum boundary

This mode cannot replace live Ethereum mainnet consensus. Ethereum mainnet support remains the external-client stack:

```bash
agi chain ethereum-plan --mode full
agi chain ethereum-plan --mode archive
agi chain ethereum-plan --mode validator --fee-recipient 0x0000000000000000000000000000000000000000
```

Use Ethereum-derived replica mode only with a new chain ID and custom genesis.
