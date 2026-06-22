# AGILANG One-Command Blockchain Setup

Branch: `evm-chain-implementations`

AGILANG blockchain tooling follows this design:

> Simple outside. Modular inside.

A developer should not need to manually assemble the chain database, validator profile, consensus engine, mempool, JSON-RPC server, staking configuration, genesis file, wallet folders and Ethereum client configuration. The runtime generator creates the starter from one command.

## Generate a blockchain app

```bash
agi chain init my-chain
```

Equivalent commands:

```bash
agi blockchain new my-chain
agi new my-chain --template blockchain
```

## Generated structure

```text
my-chain/
├─ agilang.toml
├─ .env.example
├─ .gitignore
├─ src/main.agi
├─ src/chain.agi
├─ src/devnet.agi
├─ src/staking.agi
├─ scripts/start_rpc_server.py
├─ scripts/chain_status.py
├─ config/genesis.json
├─ config/validators.json
├─ config/rpc.json
├─ config/network.json
├─ config/staking.json
├─ config/ethereum-clients.json
├─ config/wallets/wallets.example.json
├─ storage/logs/
└─ docs/
```

## Run the generated blockchain

```bash
cd my-chain
agi run
```

## Check status

```bash
agi chain status
```

or:

```bash
agi run src/chain.agi
```

## Start RPC for local wallet testing

```bash
agi chain rpc
```

Default local RPC:

```text
http://127.0.0.1:8545
```

Default chain ID:

```text
1900 / 0x76c
```

## Ethereum external-client tooling

```bash
agi chain ethereum-clients
agi chain ethereum-detect
agi chain ethereum-plan --mode full
agi chain ethereum-plan --mode archive
agi chain ethereum-plan --mode validator
agi chain ethereum-write-config --mode full
agi chain ethereum-check
agi chain ethereum-start --mode full --dry-run
```

## Boundary

AGILANG/SBQ custom-chain mode can generate and run a local or staging blockchain profile. Ethereum mainnet validation still requires real Ethereum execution, consensus and validator clients. AGILANG orchestrates those clients; it does not replace Ethereum consensus.

## Safety rule

The generator creates example wallet configuration only. Real operational signing material and production environment values should stay outside public source control.
