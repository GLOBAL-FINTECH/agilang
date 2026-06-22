# AGILANG CLI Reference

AGILANG provides two command names:

```bash
agi
agilang
```

Both are intended to route to the installed AGILANG runtime CLI.

## Version

```bash
agi --version
agilang --version
```

## Run a program

```bash
agi run src/main.agi
```

## Serve a web app

```bash
agi serve src/main.agi --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Create a normal app

```bash
agi new my-web-app
```

Recommended next step:

```bash
cd my-web-app
agi serve src/main.agi --host 127.0.0.1 --port 8000
```

## Create a blockchain app

```bash
agi new my-chain --template blockchain
```

Alternative forms may be supported by runtime branches:

```bash
agi chain init my-chain
agi blockchain new my-chain
```

## Check project files

```bash
agi check src tests
```

## Run tests

```bash
agi test
agi run tests/test_main.agi
```

## Beacon commands

```bash
agi beacon capabilities
agi beacon init
agi beacon status
agi beacon validators
agi beacon produce-block
agi beacon attest
agi beacon finalize
agi beacon fork-choice
agi beacon simulate --validators 64 --epochs 10
```

## Ethereum private-fork consensus commands

```bash
agi chain ethereum-consensus-capabilities
agi chain consensus-replacement-plan --network private-fork --consensus ethereum-pos-replica --chain-id 901900
agi chain ethereum-consensus-write-config --chain-id 901900
agi chain ethereum-consensus-check
agi chain ethereum-consensus-sim
agi chain plan --mode ethereum-consensus-replica
agi chain start --mode ethereum-consensus-replica --config config/network.json
```

## Ethereum external-client commands

```bash
agi chain ethereum-clients
agi chain ethereum-detect
agi chain ethereum-jwt --jwt-secret ethereum-data/jwt.hex
agi chain ethereum-write-config --mode full
agi chain ethereum-plan --mode archive
agi chain ethereum-check
agi chain ethereum-start --mode validator --dry-run
```

## Recommended command philosophy

AGILANG should stay beginner-friendly:

```text
one command to generate
one config to edit
one command to run
```

Advanced users can still split services into validator, RPC, archive, bootnode, and indexer modes.
