# SBQ Blockchain Network Status

Branch: `evm-chain-implementations`

This document records the current SBQ blockchain network milestone for AGILANG's EVM-chain implementation track.

## Status Summary

The SBQ blockchain starter has reached a functional local/staging milestone with:

- mainnet-profile configuration enabled
- proof-of-stake consensus profile
- signed block requirement enabled
- sequential block production
- persisted chain height/head state
- Ethereum-style JSON-RPC server
- MetaMask-compatible local network configuration
- 18-decimal EVM-style balances
- wallet balance and nonce read support

This is a working local/staging blockchain development network. It should not be described as a production public-value mainnet until cryptographic networking, signed transaction handling, validator security, slashing economics, peer scoring, denial-of-service protections, and independent security review are complete.

## Mainnet Profile Configuration

The blockchain starter uses a mainnet-style profile for stricter local/staging validation:

```text
mainnet_profile = true
require_block_signatures = true
consensus = pos
fork_choice = stake_weighted_height
chain_id = 1900
currency_symbol = SBQ
balance_decimals = 18
```

Expected active capabilities include:

- canonical SQLite-backed chain database
- mempool validation
- transaction replacement rules
- gas price ordering
- capacity limits
- duplicate rejection
- proof-of-stake consensus
- delegated proof-of-stake aliases
- weighted validator selection
- block proposer validation
- finality depth
- canonical reorg handling
- validator signature hooks
- EVM runtime bridge hooks

## Continuous Node Operation

The local starter supports sequential block production. Repeated runs continue chain height instead of resetting the chain.

Recommended command examples:

```powershell
agi run
agi run src/main.agi
agi run src/chain.agi
```

A long-running node mode should be exposed as a first-class CLI command in future releases:

```powershell
agi chain start --mode validator
agi chain status
agi chain head
agi chain finalized
agi chain validators
agi chain mempool
```

## JSON-RPC Server

The local JSON-RPC server runs on:

```text
http://127.0.0.1:8545
```

Verified local/staging methods:

| Method | Expected behavior |
|---|---|
| `eth_chainId` | Returns `0x76c`, which is chain ID `1900` in hex |
| `eth_blockNumber` | Returns the current block height |
| `eth_getBalance` | Returns account balance in wei-style 18-decimal format |
| `eth_getTransactionCount` | Returns account nonce |
| `net_version` | Returns `1900` |
| `web3_clientVersion` | Returns the SBQ/AGILANG client version |

Example chain ID check:

```powershell
curl -X POST http://127.0.0.1:8545 -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_chainId\",\"params\":[],\"id\":1}"
```

Expected result:

```json
{"jsonrpc":"2.0","id":1,"result":"0x76c"}
```

## MetaMask Local Network Configuration

Add a custom network in MetaMask:

| Field | Value |
|---|---|
| Network name | `AGILANG SBQ Local` |
| RPC URL | `http://127.0.0.1:8545` |
| Chain ID | `1900` |
| Currency symbol | `SBQ` |
| Decimals | `18` |

Users should be able to connect MetaMask to the local network and read chain ID, network version, block height, balances, and nonces.

## Wallet Security Rule

Wallet configuration files may exist locally for testing, but private keys must not be committed to the repository.

Recommended `.gitignore` rules:

```gitignore
config/wallets/*.json
config/wallets/*.key
*.pem
*.key
.env
storage/*.sqlite
storage/*.db
```

Documentation may refer to wallet file paths, but public repository docs must not include real private keys, mnemonic phrases, seed phrases, or signing keys.

## Production Boundary

The current implementation should be described as:

```text
MetaMask-compatible local/staging SBQ blockchain network foundation.
```

Do not describe it as a public real-value mainnet until the following are complete:

- audited Ethereum signed raw transaction support
- RLP/EIP-155/EIP-1559 transaction decoding
- Keccak-256 transaction hashing where Ethereum compatibility requires it
- secp256k1 public key recovery
- persistent peer discovery
- production P2P networking
- peer scoring and banning
- validator key isolation
- slashing economics
- staking join/exit lifecycle
- validator monitoring
- DoS/rate-limit hardening
- archive node mode
- RPC node separation from validator nodes
- independent security review

## Recommended Next Implementation Milestones

1. Convert `scripts/start_rpc_server.py` into a first-class CLI command.
2. Add `agi chain start --mode validator` as a long-running node process.
3. Add `agi chain rpc --host 127.0.0.1 --port 8545`.
4. Add `agi chain status`, `agi chain head`, and `agi chain validators`.
5. Add multi-node local peer sync testing.
6. Add validator join/stake/exit commands.
7. Add transaction receipt lookup over JSON-RPC.
8. Add MetaMask transaction submission support only after audited raw transaction validation.
9. Add smart contract tooling: compile, deploy, call, event logs, and gas reports.

## Recommended Documentation Wording

Use this wording in public documentation:

> AGILANG blockchain apps are designed as single-command chain runtimes with modular internal services. Developers can start a complete local chain, validator node, RPC node, archive node, or bootnode from one configuration file while still being able to separate services for production networks.

## Final Milestone Statement

The SBQ blockchain network has reached a functional local/staging milestone with proof-of-stake block production, signed-block enforcement, persistent chain state, JSON-RPC read APIs, and MetaMask local-network compatibility.
