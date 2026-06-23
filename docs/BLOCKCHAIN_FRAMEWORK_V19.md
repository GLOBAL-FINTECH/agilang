# AGILANG v1.9.3 Mainnet-Capable Blockchain Framework Edition

AGILANG v1.9.3 includes the v1.9 blockchain layer and adds pluggable consensus plus mainnet-profile hardening. It is intended to give developers the missing modules around the v1.8 EVM runtime: peer-to-peer sync, selectable consensus, fork choice, block production, chain storage and mempool management.

## Included modules

- Proof-of-Stake consensus engine with weighted validator selection
- DPoS/DPO consensus engine with delegation-weighted producer selection
- Dev consensus engine for deterministic local simulation
- mainnet-profile config with strict accounting, nonce ordering and required block signatures
- validator block-signature hooks and signature verification during validation
- proposer validation and block validation
- canonical fork-choice using stake-weighted height scoring
- persistent SQLite chain database for blocks, transactions, metadata and state
- managed mempool with duplicate rejection, nonce replacement, invalid-field checks and gas-price ordering
- block production with gas limit, transaction root, receipts root, state root and gas-used validation
- in-process p2p/devnet harness with transaction and block gossip
- EVM execution hooks for contract deployment and local calls
- CLI commands for genesis, mempool demos, block production and devnet testing
- `--template blockchain` project scaffold

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

## Useful CLI commands

```bash
agi blockchain capabilities
agi blockchain demo
agi blockchain simulate-consensus
agi blockchain init-genesis --consensus pos --db storage/chain.sqlite --validator alice:60 --validator bob:40
agi blockchain init-genesis --consensus dpo --validator alice:60 --validator bob:40
agi blockchain mempool-demo --consensus pos --sender alice --to bob --value 10
agi blockchain produce-block --consensus dev --validator alice --to bob --value 10
agi blockchain devnet --consensus dpos --blocks 3
```


## v1.9.3 mainnet-capable consensus notes

The v1.9.3 release adds selectable consensus and a stricter mainnet-style profile without breaking the older v1.9 workflow:

- native C runtime version metadata is aligned with the package release;
- Linux prebuilt runtime artifacts are rebuilt and hash-verified;
- `consensus_mode="pos"` selects weighted Proof-of-Stake;
- `consensus_mode="dpos"` or `"dpo"` selects delegated producer voting;
- `consensus_mode="dev"` selects deterministic local consensus for simulation;
- `blockchain_mainnet_config()` enables strict accounting, nonce ordering, required validator signatures, higher finality depth and non-zero minimum gas price;
- block validation checks validator signatures when signatures are required or supplied;
- duplicate transaction hashes are rejected at mempool admission;
- invalid negative values, nonces and gas prices are rejected;
- optional `strict_accounting=True` enables balance and nonce validation;
- imported blocks are re-executed against parent state and forged receipts/state roots are rejected;
- canonical balances, contracts and nonces are replayed after fork-choice updates/reorgs using successful receipts only.

Use `strict_accounting=True` when you want private-chain behavior closer to account-based production chains. Keep it `False` for protocol experiments where you intentionally want permissive state transitions.

## Architecture

```text
AGILANG blockchain app
  -> pluggable PoS / DPoS-DPO / Dev consensus
  -> optional mainnet-profile signature validation
  -> mempool admission/replacement/ordering
  -> block producer
  -> block validator
  -> fork choice/canonical DB
  -> p2p/devnet sync
  -> EVM runtime hooks
```

## Production boundary

This is a mainnet-capable framework profile for simulation, staging and custom-chain development, not a finished drop-in public mainnet client. Before running real-value public networks, add audited cryptographic networking/signing, slashing economics, peer scoring, network DoS controls, persistent peer discovery, state tries, pruning, checkpointing, metrics, observability and independent consensus review.
