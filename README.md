# AGILANG EVM Chain Implementations

Branch: `evm-chain-implementations`

This branch is dedicated to AGILANG/SBQ EVM chain implementation work, JSON-RPC, local wallet compatibility, SBQ custom-chain experiments, and Ethereum external-client orchestration.

The stable runtime remains on `main`. The public web app starter remains on `blog`.

## One-command blockchain app generator

The runtime now includes a first-class blockchain app generator:

```bash
agi chain init my-chain
```

Equivalent commands:

```bash
agi blockchain new my-chain
agi new my-chain --template blockchain
```

The generated project includes source files, configs, JSON-RPC setup, validator/staking config, genesis config, Ethereum external-client config, docs and example wallet placeholders.

See:

- `agilang/blockchain_runtime_gateway.py`
- `agilang/cli_runtime.py`
- `docs/EASIEST_BLOCKCHAIN_SETUP.md`
- `tests/test_runtime_blockchain_generator.py`

## Run generated chain

```bash
cd my-chain
agi run
agi chain status
agi chain rpc
```

Default local RPC: `http://127.0.0.1:8545`

Default chain ID: `1900 / 0x76c`

## Current SBQ network status

The SBQ blockchain starter has reached a functional local/staging milestone with proof-of-stake block production, signed-block enforcement, persistent chain state, JSON-RPC read APIs, and local wallet network compatibility.

See:

- `docs/SBQ_BLOCKCHAIN_NETWORK_STATUS.md`

## Ethereum external-client runtime status

AGILANG v2.0.0 adds an Ethereum external-client runtime layer. This allows AGILANG to generate configuration, validate ports, detect installed clients, plan startup commands, and optionally supervise real Ethereum execution, consensus, and validator clients.

Supported roles:

- execution clients: Geth, Nethermind, Besu, Erigon
- consensus/beacon clients: Lighthouse, Prysm, Teku, Nimbus, Lodestar
- validator clients: Lighthouse, Prysm, Teku, Nimbus, Lodestar

Important boundary: AGILANG/SBQ custom consensus does not validate Ethereum mainnet directly. Ethereum mainnet validation must be performed by the real Ethereum execution, consensus, and validator client stack.

See:

- `docs/ETHEREUM_CLIENT_STACK_V20.md`
- `agilang/ethereum_clients.py`
- `tests/test_v20_ethereum_clients.py`

## Install locally

```bash
git clone https://github.com/GLOBAL-FINTECH/agilang.git
cd agilang
git checkout evm-chain-implementations
python -m pip install -e .
agi --version
```

## Ethereum client commands

```bash
agi chain ethereum-clients
agi chain ethereum-detect
agi chain ethereum-write-config --mode full
agi chain ethereum-plan --mode full
agi chain ethereum-plan --mode archive
agi chain ethereum-plan --mode validator
agi chain ethereum-check
agi chain ethereum-start --mode full --dry-run
```
