# AGILANG Getting Started Guide

This guide teaches the first steps for using AGILANG as a programming language and application runtime.

## 1. Install the runtime

```bash
git clone https://github.com/GLOBAL-FINTECH/agilang.git
cd agilang
python -m pip install -e .
agi --version
```

Expected:

```text
AGILANG 2.1.0
```

## 2. Create your first program

Create `hello.agi`:

```agi
fn main() -> i32:
    print("Hello from AGILANG")
    return 0
```

Run it:

```bash
agi run hello.agi
```

## 3. Create a web app

```bash
agi new my-web-app
cd my-web-app
agi serve src/main.agi --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## 4. Create a blockchain app

```bash
agi new my-chain --template blockchain
cd my-chain
agi run
agi run src/chain.agi
agi run src/beacon.agi
```

The blockchain generator creates the chain runtime files, config files, wallet example file, Beacon config, Ethereum private-fork config, RPC config, staking config, and documentation.

## 5. Understand the file types

| File type | Purpose |
|---|---|
| `.agi` | AGILANG source code: routes, services, controllers, CLI scripts, blockchain modules |
| `.ags` | AGS reactive templates for web pages |
| `.toml` | Project configuration |
| `.json` | Runtime, app, network, chain, or service configuration |
| `.sql` | Database migrations |

## 6. Recommended learning path

1. Run `hello.agi`.
2. Learn variables, functions, structs, enums, imports, and control flow.
3. Create a web app.
4. Learn `.ags` templates.
5. Add routes and JSON APIs.
6. Add database storage.
7. Add authentication and email configuration in a starter app.
8. Generate a blockchain app only after the normal runtime basics are understood.

## 7. Main commands

```bash
agi --version
agi run src/main.agi
agi serve src/main.agi --host 127.0.0.1 --port 8000
agi check src tests
agi test
agi new my-web-app
agi new my-chain --template blockchain
agi beacon status
agi beacon simulate --validators 64 --epochs 10
```

## 8. Next documents

- `docs/LANGUAGE_GUIDE.md`
- `docs/CLI_REFERENCE.md`
- `docs/APPLICATIONS_AND_STARTERS.md`
- `docs/BLOCKCHAIN_APP_GENERATOR.md`
