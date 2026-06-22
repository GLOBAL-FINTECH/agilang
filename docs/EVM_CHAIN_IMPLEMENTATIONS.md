# AGILANG EVM Chain Implementations

Branch: `evm-chain-implementations`

This branch is dedicated to AGILANG/SBQ EVM chain implementation work. It is separate from `main` so the stable AGILANG runtime remains clean while EVM, JSON-RPC, wallet, and MetaMask-facing work can move faster.

## Purpose

Use this branch for:

- Ethereum-style JSON-RPC support
- MetaMask-compatible local network configuration
- SBQ/EVM chain experiments
- EVM execution integration
- wallet/app read APIs
- local development transaction submission
- chain smoke tests
- production-hardening notes for future public-chain work

## Recommended local workflow

```bash
git clone https://github.com/GLOBAL-FINTECH/agilang.git
cd agilang
git checkout evm-chain-implementations
python -m pip install -e .
agi --version
```

## Blockchain app creation

```bash
agi new my chain --template blockchain
cd my-chain
agi run
agi run src/chain.agi
agi run src/mempool.agi
agi run src/devnet.agi
agi run src/evm_contract.agi
```

## JSON-RPC / MetaMask foundation

The uploaded AGILANG v1.9.6 package was reviewed locally and includes a JSON-RPC foundation for wallet/app connectivity.

Recommended local RPC command:

```bash
agi blockchain rpc-server --config config/rpc.json --db storage/chain.sqlite --auto-mine --dev-send
```

Recommended smoke command:

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

## RPC methods target

The EVM implementation branch should cover these methods first:

- `web3_clientVersion`
- `net_version`
- `net_listening`
- `net_peerCount`
- `eth_chainId`
- `eth_protocolVersion`
- `eth_syncing`
- `eth_mining`
- `eth_accounts`
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
- `eth_sendRawTransaction` for supported AGILANG transaction envelopes
- optional `eth_sendTransaction` for local development only

## MetaMask network setup

In MetaMask, add a custom network:

| Field | Value |
|---|---|
| Network name | `AGILANG SBQ Local` |
| RPC URL | `http://127.0.0.1:8545` |
| Chain ID | `1900` |
| Currency symbol | `SBQ` |
| Block explorer | leave blank for local dev |

## Production boundary

This branch is for implementation and staging work. Before any public real-value chain launch, the EVM/RPC implementation needs independent review, production-grade key handling, validated signed transaction support, network protections, monitoring, validator operations documentation, and a security audit.

## Local validation result

The uploaded AGILANG v1.9.6 JSON-RPC/MetaMask foundation package was extracted and tested locally.

Command:

```bash
python -m pytest -q
```

Result:

```text
90 passed
```

## Promotion rule

Stable improvements from this branch should move through this path:

```text
evm-chain-implementations → dev → main
```

Do not merge experimental wallet/RPC changes directly into `main` without validation.
