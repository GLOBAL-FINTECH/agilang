# AGILANG v2.1 Native SBQ Beacon Consensus Layer

AGILANG v2.1 adds a native Beacon-chain-inspired consensus layer for SBQ/custom chains.

This is not an Ethereum mainnet validator replacement. Ethereum mainnet validation still belongs to official Ethereum execution, consensus, and validator clients. The SBQ Beacon layer is for AGILANG/SBQ private chains, staging networks, and custom networks.

## Design goal

AGILANG should make blockchain setup simple from the outside and modular inside:

```bash
agi new my chain --template blockchain
cd my-chain
agi beacon status
agi beacon produce-block
agi beacon attest
agi beacon finalize
```

A developer should be able to generate a chain, configure validators/wallets/RPC, and begin testing without manually assembling unrelated services.

## Native SBQ Beacon components

| Component | Status | Purpose |
|---|---:|---|
| Slots | Added | Fixed block-production schedule |
| Epochs | Added | Groups of slots used for checkpoints/finality |
| Validators | Added | Active validator registry with stake weights |
| Proposer selection | Added | Selects block proposer for each slot |
| Beacon blocks | Added | Consensus-layer blocks wrapping execution payloads |
| Execution payload bridge | Added | Connects beacon block production to SBQ execution payload metadata |
| Attestations | Added | Validator votes for head/source/target |
| Checkpoints | Added | Justified and finalized checkpoint state |
| Finality | Added | Checkpoint justification/finalization using stake threshold |
| Fork choice | Added | Attestation-weighted head choice |
| Validator penalty hooks | Added | Double proposal and double vote detection |
| Persistence | Added | SQLite local/staging persistence |
| CLI | Added | `agi beacon ...` command family |

## Defaults

```text
chain_id = 1900
consensus = sbq-beacon
slot_seconds = 6
slots_per_epoch = 16
finality_threshold = 66%
min_validator_stake = 1000
```

These values are configurable. Ethereum-derived private fork mode remains separate as `ethereum-pos-replica` with its own 12-second slot and 32-slot epoch replica profile.

## Commands

### Initialize Beacon state

```bash
agi beacon init
```

Optional:

```bash
agi beacon init --slot-seconds 6 --slots-per-epoch 16 --chain-id 1900
```

### Status

```bash
agi beacon status
```

### Validators

```bash
agi beacon validators
```

### Produce one Beacon block

```bash
agi beacon produce-block
```

### Create attestations for the current head

```bash
agi beacon attest
```

### Process checkpoint finality

```bash
agi beacon finalize
```

### Run fork choice

```bash
agi beacon fork-choice
```

### Simulate epochs

```bash
agi beacon simulate --validators 64 --epochs 10
```

## Generated blockchain starter files

`agi new my chain --template blockchain` now includes:

```text
src/beacon.agi
config/beacon.json
storage/beacon.sqlite
docs/SBQ_BEACON_CHAIN_V21.md
```

The starter also continues to generate Ethereum external-client and Ethereum PoS replica configuration files for private Ethereum-derived fork work.

## Architecture boundary

| Mode | Consensus |
|---|---|
| SBQ native chain | `sbq-beacon` or legacy AGILANG PoS/DPoS/dev |
| Ethereum-derived private fork | `ethereum-pos-replica` |
| Ethereum mainnet connectivity | Real external Ethereum clients |
| Ethereum mainnet validation | Official Ethereum consensus/validator clients only |

## Production boundary

The native SBQ Beacon layer is suitable for local development, private networks, simulations, and staging.

Before public real-value operation, add:

- audited cryptographic signing
- validator key isolation
- hardened peer-to-peer networking
- peer scoring
- validator penalty economics
- DoS hardening
- long-running supervisor
- multi-node sync tests
- archive/indexer separation
- monitoring and alerting
- independent security review
