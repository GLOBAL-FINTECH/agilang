# AGILANG v2.0.0 Ethereum External Clients Validation

## Version

```text
AGILANG 2.0.0
```

## Scope

This validation covers the uploaded `AGILANG_v2_0_0_ethereum_external_clients_runtime` package and records the Ethereum external-client runtime layer imported into the `evm-chain-implementations` branch.

## Implemented runtime layer

- Real Ethereum execution-client orchestration.
- Real Ethereum consensus/beacon-client orchestration.
- Real Ethereum validator-client orchestration.
- Ethereum archive command planning.
- Engine API JWT secret management.
- Private Engine API and validator API port validation.
- Installed Ethereum client detection.
- Dry-run-safe startup command plans.
- One-command profiles for full, archive, validator, and all-in-one Ethereum client stack planning.

## Supported clients

| Role | Supported clients |
|---|---|
| Execution | Geth, Nethermind, Besu, Erigon |
| Consensus / Beacon | Lighthouse, Prysm, Teku, Nimbus, Lodestar |
| Validator | Lighthouse, Prysm, Teku, Nimbus, Lodestar |

## CLI validation commands

```bash
PYTHONPATH=. python -m agilang --version
PYTHONPATH=. python -m agilang chain ethereum-plan --mode validator --fee-recipient 0x0000000000000000000000000000000000000000
PYTHONPATH=. python -m agilang chain ethereum-check
PYTHONPATH=. python -m agilang blockchain mainnet-check
```

Expected behavior:

```text
ok: true
execution client plan: present
consensus client plan: present
validator client plan: present when enabled
engine API: private loopback
validator API: private loopback
```

## Local test results

Executed locally from the extracted uploaded package:

```bash
PYTHONPATH=. pytest tests/test_v20_ethereum_clients.py -q
```

Result:

```text
10 passed
```

Combined blockchain and Ethereum external-client suite:

```bash
PYTHONPATH=. pytest tests/test_v19_blockchain.py tests/test_v19_maintenance_tuning.py tests/test_v20_ethereum_clients.py -q
```

Result:

```text
29 passed
```

## Safety boundary

AGILANG does not replace Ethereum consensus. AGILANG/SBQ custom PoS/DPoS/dev consensus is for SBQ/custom-chain operation. Ethereum mainnet validation must be handled by real Ethereum execution, consensus/beacon, and validator clients.

The imported v2.0.0 layer should be described as:

```text
Ethereum external-client orchestration and supervision layer for AGILANG.
```

It should not be described as:

```text
Native AGILANG custom consensus validating Ethereum mainnet.
```

## Production notes

Before using this in production, operators should still configure:

- hardened firewall rules
- private Engine API and validator API binding
- secure JWT secret storage
- encrypted validator key storage
- client-specific update policy
- monitoring and alerting
- backup/recovery process
- independent security review
