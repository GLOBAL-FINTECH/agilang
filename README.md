# AGILANG EVM Chain Implementations

Branch: `evm-chain-implementations`

This branch is dedicated to AGILANG/SBQ EVM chain implementation work, JSON-RPC, MetaMask-compatible local-network support, wallet/app connectivity research, and Ethereum external-client orchestration.

The stable runtime remains on `main`. The public web app starter remains on `blog`.

## Branch purpose

Use this branch for:

- EVM execution integration
- Ethereum-style JSON-RPC server work
- MetaMask-compatible local network testing
- SBQ custom-chain experiments
- wallet read APIs
- transaction receipt and block lookup APIs
- RPC smoke tests
- chain implementation documentation
- Ethereum execution-client orchestration
- Ethereum consensus/beacon-client orchestration
- Ethereum validator-client orchestration
- archive-node command planning
- Engine API JWT secret management

## Current SBQ network status

The SBQ blockchain starter has reached a functional local/staging milestone with proof-of-stake block production, signed-block enforcement, persistent chain state, JSON-RPC read APIs, and MetaMask local-network compatibility.

See:

- `docs/SBQ_BLOCKCHAIN_NETWORK_STATUS.md`

## Ethereum external-client runtime status

AGILANG v2.0.0 adds a first-class Ethereum external-client runtime layer. This closes the earlier implementation gap by allowing AGILANG to generate configuration, validate ports, create Engine API JWT secrets, detect installed clients, plan startup commands, and optionally supervise real Ethereum execution, consensus, and validator clients.

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

## JSON-RPC local network

Start the local RPC server:

```bash
agi blockchain rpc-server --config config/rpc.json --db storage/chain.sqlite --auto-mine --dev-send
```

Run the smoke test:

```bash
agi blockchain rpc-smoke
```

Default local network values:

| Setting | Value |
|---|---|
| RPC URL | `http://127.0.0.1:8545` |
| Chain ID | `1900` |
| Currency symbol | `SBQ` |
| Decimals | `18` |

## MetaMask local setup

Add a custom network in MetaMask:

| Field | Value |
|---|---|
| Network name | `AGILANG SBQ Local` |
| RPC URL | `http://127.0.0.1:8545` |
| Chain ID | `1900` |
| Currency symbol | `SBQ` |

## Ethereum external-client commands

```bash
agi chain ethereum-clients
agi chain ethereum-detect
agi chain ethereum-jwt --jwt-secret ethereum-data/jwt.hex
agi chain ethereum-write-config --mode full
agi chain ethereum-write-config --mode archive
agi chain ethereum-write-config --mode validator --fee-recipient 0x0000000000000000000000000000000000000000
agi chain ethereum-plan --mode full
agi chain ethereum-plan --mode archive
agi chain ethereum-plan --mode validator --fee-recipient 0x0000000000000000000000000000000000000000
agi chain ethereum-check
agi chain ethereum-start --mode full --dry-run
agi chain ethereum-start --mode archive --dry-run
agi chain ethereum-start --mode validator --dry-run
```

## Target JSON-RPC methods

- `web3_clientVersion`
- `net_version`
- `net_listening`
- `net_peerCount`
- `eth_chainId`
- `eth_blockNumber`
- `eth_gasPrice`
- `eth_getBalance`
- `eth_getTransactionCount`
- `eth_getBlockByNumber`
- `eth_getBlockByHash`
- `eth_getTransactionByHash`
- `eth_getTransactionReceipt`
- `eth_getCode`
- `eth_estimateGas`
- `eth_call`
- `eth_sendRawTransaction`
- optional `eth_sendTransaction` for local development only

## Documentation

- `docs/SBQ_BLOCKCHAIN_NETWORK_STATUS.md`
- `docs/ETHEREUM_CLIENT_STACK_V20.md`
- `docs/EVM_CHAIN_IMPLEMENTATIONS.md`
- `docs/JSON_RPC_METAMASK_V19_6.md`
- `docs/BLOCKCHAIN_FRAMEWORK_V19.md`
- `docs/EVM_PRODUCTION_RUNTIME_V18.md`
- `docs/EVM_TOOLING_V16.md`

## Local validation

The uploaded AGILANG v1.9.6 JSON-RPC/MetaMask foundation package was extracted and tested locally.

```text
90 passed
```

The uploaded AGILANG v2.0.0 Ethereum external-client runtime package was extracted and tested locally.

```text
PYTHONPATH=. pytest tests/test_v20_ethereum_clients.py -q
10 passed

PYTHONPATH=. pytest tests/test_v19_blockchain.py tests/test_v19_maintenance_tuning.py tests/test_v20_ethereum_clients.py -q
29 passed
```

## Production boundary

This branch is for implementation and staging work. Before a public chain launch, add audited signed transaction support, stronger key handling, production network protections, monitoring, validator operations documentation, and an independent security review.

For Ethereum mainnet connectivity, AGILANG must rely on external Ethereum clients for execution, consensus, and validator duties. Do not describe SBQ/AGILANG custom consensus as an Ethereum mainnet validator.

## Promotion path

Stable work should move through:

```text
evm-chain-implementations → dev → main
```
