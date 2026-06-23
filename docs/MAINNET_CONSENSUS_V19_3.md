# AGILANG v1.9.3 Mainnet Consensus Runbook

AGILANG v1.9.3 adds selectable blockchain consensus modes and a stricter mainnet-profile configuration for simulation, staging and custom-chain development.

## Consensus modes

| Mode | Alias | Purpose |
|---|---|---|
| `pos` | `proof_of_stake` | Weighted validator Proof-of-Stake proposer selection. |
| `dpos` | `dpo`, `delegated_proof_of_stake` | Delegation-weighted producer selection. |
| `dev` | `developer`, `dev_consensus` | Deterministic local consensus for fast devnet/simulation work. |

## Mainnet profile

Use `blockchain_mainnet_config()` when a chain should behave closer to a real account-based network:

```agi
let cfg = blockchain_mainnet_config(
  chain_id=1933,
  name="agilang-mainnet-profile",
  consensus_mode="pos",
  validators={"alice": 100, "bob": 80},
  validator_signing_keys={"alice": "alice-secret", "bob": "bob-secret"},
  genesis_state={"balances": {"alice": 1000, "bob": 100}},
  slot_seconds=1
)
```

This profile enables:

- strict balance accounting;
- strict nonce ordering;
- required validator block signatures;
- non-zero minimum gas price;
- higher finality depth;
- future-timestamp drift checks.

## Simulation command

```bash
agi blockchain simulate-consensus
```

Expected high-level result:

```json
{
  "ok": true,
  "scenarios": [
    {"consensus_mode": "pos", "synced": true},
    {"consensus_mode": "dpos", "synced": true},
    {"consensus_mode": "dev", "synced": true},
    {"mainnet_profile": true, "signed": true, "synced": true}
  ]
}
```

## Production boundary

The v1.9.3 mainnet profile is a framework-level hardening layer. For a public real-value mainnet, replace the local deterministic signature hook with audited cryptographic validator keys, add persistent peer discovery, peer scoring, slashing economics, DoS controls, state tries, pruning/snapshots, observability, formal fork-choice review and independent security audits.
