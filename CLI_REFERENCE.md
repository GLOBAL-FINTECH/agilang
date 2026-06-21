# AGILANG CLI Reference

This command reference was prepared by scanning the AGILANG v2.1.0 CLI implementation and running the local CLI help commands.

## Global Commands

```bash
agilang --version
agilang -h
agi --version
agi -h
```

`agi` is a short alias for `agilang` when installed.

---

## Core Development Commands

| Command | Purpose | Example |
|---|---|---|
| `run` | Transpile and execute `.agi` source | `agilang run src/main.agi` |
| `check` | Static-check files or folders | `agilang check src tests` |
| `to-py` | Transpile `.agi` to Python | `agilang to-py src/main.agi --line-map` |
| `build` | Build a standalone Python launcher | `agilang build src/main.agi -o build/app.py` |
| `fmt` | Format AGILANG files | `agilang fmt src -w` |
| `test` | Run `.agi` test files | `agilang test` |
| `tokens` | Print lexical tokens | `agilang tokens src/main.agi` |
| `ast` | Print compiler AST JSON | `agilang ast src/main.agi --pretty` |
| `typecheck` | Run AST-level type checker | `agilang typecheck src tests` |
| `repl` | Interactive shell | `agilang repl` |
| `doctor` | Environment diagnostics | `agilang doctor` |

### `run`

```bash
agilang run [file] [--dump] [--check]
```

Examples:

```bash
agilang run src/main.agi
agilang run src/main.agi --check
agilang run src/main.agi --dump
```

### `serve`

```bash
agilang serve <file> --host 127.0.0.1 --port 8000
```

Shortcut:

```bash
agi serve src/main.agi --8000
```

> `--8000` is normalized to `--port 8000` only for the `serve` command.

---

## Project Generation Commands

| Command | Purpose | Example |
|---|---|---|
| `new` | Create new project | `agilang new myapp` |
| `make:page` | Create AGS page | `agilang make:page pricing` |
| `make:component` | Create AGS component | `agilang make:component stat-card` |
| `make:api` | Create API handler snippet | `agilang make:api home-stats` |

### `new`

```bash
agilang new <name> [--template web|web-live|api|basic|systems|zk|blockchain] [--dir DIR] [--force]
```

Examples:

```bash
agilang new myapp
agilang new social app
agilang new apiapp --template api
agilang new chainapp --template blockchain
agilang new systemsapp --template systems
```

Template aliases supported by scaffold code:

```text
web-live, web-ags, ags, reactive -> web
```

### `make:page`

```bash
agilang make:page profile
```

Creates:

```text
resources/views/profile.ags
```

### `make:component`

```bash
agilang make:component user-card
```

Creates:

```text
resources/views/components/user-card.ags
```

### `make:api`

```bash
agilang make:api home-stats
```

Creates:

```text
src/api/home_stats.agi
```

---

## Package Commands

```bash
agilang pkg init
agilang pkg add <name> <spec>
agilang pkg remove <name>
agilang pkg list
agilang pkg install
agilang pkg pack
```

Examples:

```bash
agilang pkg init --name myapp
agilang pkg add auth path:../authlib
agilang pkg add ui git+https://github.com/example/agilang-ui.git
agilang pkg list
agilang pkg pack -o dist/myapp.agipkg
```

---

## Database Commands

```bash
agilang db create
agilang db migrate
agilang db status
agilang db refresh migrate
agilang db refresh-migrate
agilang db table create <table> --columns "name:VARCHAR(255),email:VARCHAR(255) UNIQUE"
agilang db table add-column <table> <column> <definition>
agilang db table drop-column <table> <column>
agilang db table drop <table>
```

The database command scans `.env` / `.env.example` for:

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=devapp_blog
```

PyMySQL is required for MySQL database automation:

```bash
pip install -r requirements.txt
```

---

## Web / Hosting Commands

```bash
agilang hosting capabilities
agilang hosting doctor
agilang hosting scaffold --root . --entry src/main.agi --target public_html --mode auto
```

Modes:

```text
auto
cgi
fastcgi
passenger
```

Generated files commonly include:

```text
public_html/app.cgi
public_html/app.fcgi
public_html/.htaccess
passenger_wsgi.py
```

---

## React / Client Commands

```bash
agilang react web <name>
agilang react mobile <name>
agilang react sdk
```

Use this when building React or React Native clients that connect to an AGILANG backend.

---

## Runtime Commands

```bash
agilang runtime status
agilang runtime build
agilang runtime doctor
agilang runtime prebuilt-status
agilang runtime install-prebuilt
agilang runtime platform-matrix
```

These inspect or build the AGILANG native C + Python hybrid runtime.

---

## Mobile Commands

```bash
agilang mobile platform-matrix
agilang mobile capabilities
agilang mobile doctor
agilang mobile native-bridge <name>
```

Use for Android/iOS bridge exploration and React Native integrations.

---

## Low-Level Networking Commands

```bash
agilang net capabilities
agilang net doctor
```

Provides low-level TCP/UDP/packet/gossip capability diagnostics.

---

## EVM / Web3 Commands

```bash
agilang evm capabilities
agilang evm selector "transfer(address,uint256)"
agilang evm calldata "transfer(address,uint256)" --types address,uint256 --values 0xabc...,100
agilang evm abi-encode "uint256,string" "100,hello"
agilang evm abi-decode "uint256" 0x...
agilang evm disasm 0x6001600201
agilang evm run 0x600160020100 --trace
agilang evm simulate-call 0x...
agilang evm estimate-gas 0x...
agilang evm trace 0x...
agilang evm unsigned-tx --nonce 1 --gas-price 1000000000 --gas-limit 21000 --to 0x... --value 1 --chain-id 1
agilang evm external-engine auto
agilang evm build-demo
```

---

## Zero-Knowledge Commands

```bash
agilang zk capabilities
agilang zk bridge-status
agilang zk commit "secret-value" --salt my-salt
agilang zk verify-commit <commitment> "secret-value" --salt my-salt
agilang zk merkle-demo --leaves alice,bob,carol --index 1
agilang zk schnorr-demo --secret 12345 --message agilang
agilang zk circuit-demo --x 7
agilang zk demo
```

---

## Systems Commands

```bash
agilang systems capabilities
agilang systems doctor
agilang systems interop
```

Used for general systems-language capability and Python/C interop diagnostics.

---

## Blockchain Commands

```bash
agilang blockchain capabilities
agilang blockchain demo
agilang blockchain simulate-consensus
agilang blockchain init-genesis --chain-id 1900 --name agilang-chain --consensus pos --validator alice:100
agilang blockchain mempool-demo --sender alice --to bob --value 10
agilang blockchain produce-block --validator alice --to bob --value 10
agilang blockchain devnet --blocks 2 --consensus pos
agilang blockchain merkle-root "a,b,c"
```

Consensus modes:

```text
pos
dpos
dpo
dev
```

---

## Native C Backend Commands

```bash
agilang to-c src/main.agi -o build/main.c
agilang native-build src/main.agi -o build/main
agilang backends
```

Use these for C backend and native executable experiments.

---

## Language Server

```bash
agilang lsp
```

Starts the AGILANG language server over stdio for editor integration.
