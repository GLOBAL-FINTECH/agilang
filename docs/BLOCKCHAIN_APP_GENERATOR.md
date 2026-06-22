# AGILANG Blockchain App Generator

AGILANG includes a blockchain project generator so a developer can create a complete configurable chain starter from one command.

The goal is:

```text
install AGILANG -> run one command -> configure chain -> start local node/RPC -> connect wallet tooling
```

## Generate a blockchain app

```bash
agi new my-chain --template blockchain
```

Then:

```bash
cd my-chain
agi run
agi run src/chain.agi
agi run src/beacon.agi
```

## Generated files

```text
my-chain/
├─ src/
│  ├─ main.agi
│  ├─ chain.agi
│  ├─ beacon.agi
│  ├─ staking.agi
│  ├─ network.agi
│  ├─ ethereum_clients.agi
│  └─ ethereum_consensus.agi
├─ config/
│  ├─ genesis.json
│  ├─ network.json
│  ├─ rpc.json
│  ├─ beacon.json
│  ├─ staking.json
│  ├─ validators.json
│  ├─ ethereum-consensus-replica.json
│  ├─ ethereum-clients.json
│  └─ wallets/wallets.example.json
├─ storage/
│  ├─ beacon.sqlite
│  └─ logs/
└─ docs/
   ├─ BLOCKCHAIN_RUNBOOK.md
   ├─ SBQ_BEACON_CHAIN_V21.md
   ├─ ETHEREUM_CONSENSUS_REPLICA_V20_2.md
   └─ METAMASK_SETUP.md
```

## What the generated chain includes

| Component | Purpose |
|---|---|
| Chain runtime | Runs the chain starter entrypoint |
| Config files | Chain ID, network, RPC, validators, Beacon, staking, Ethereum client plan |
| SBQ Beacon layer | Slots, epochs, validators, attestations, checkpoints, finality, fork choice |
| Staking config | Validator stake and participation settings |
| RPC config | Local/staging JSON-RPC endpoint settings |
| Wallet example | Example wallet config path without committing private keys |
| Ethereum replica config | Ethereum-derived private-fork consensus profile |
| External client config | Orchestration plan for real Ethereum execution/consensus/validator clients |

## Local run flow

```bash
agi run
agi run src/chain.agi
agi beacon init
agi beacon produce-block
agi beacon attest
agi beacon finalize
agi beacon status
```

## RPC flow

The local/staging RPC default is:

```text
http://127.0.0.1:8545
```

Default chain ID:

```text
1900 / 0x76c
```

## Security rule

Do not commit real private keys, mnemonic phrases, validator signing keys, wallet databases, production databases, or RPC credentials.

Use example files only:

```text
config/wallets/wallets.example.json
```

Real local files should stay ignored:

```text
config/wallets/wallets.json
*.key
*.pem
*.sqlite
storage/*.sqlite
```

## Production boundary

The generated blockchain app is suitable for local development, staging, private-chain experiments, and SBQ runtime development. Public real-value deployment requires independent security review, hardened networking, peer scoring, validator key isolation, slashing economics, rate limits, DoS protection, archive/indexer separation, and production monitoring.
