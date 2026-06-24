# AGILANG Independent Verification Checklist

Use this checklist to verify the security hardening and blockchain scaffold changes from a clean machine.

## 1. Install test dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
```

## 2. Run the full regression suite

```bash
python -m pytest -q
python -m compileall -q agilang
```

Expected result for this package:

```text
111 passed
```

## 3. Verify blockchain generation is AGILANG-native

```bash
agi new My Chain --template blockchain --force
cd my-chain
find src -maxdepth 2 -type f | sort
find resources/views -maxdepth 2 -type f | sort
```

Expected AGILANG source files:

```text
src/main.agi
src/chain.agi
src/devnet.agi
src/staking.agi
src/rpc.agi
src/explorer.agi
resources/views/layout.ags
resources/views/explorer.ags
resources/views/validator.ags
```

These Python helper scripts should not exist in a generated blockchain app:

```text
scripts/start_rpc_server.py
scripts/chain_status.py
```

## 4. Verify one-shot versus continuous blockchain behavior

One-shot commands intentionally run once and exit:

```bash
agi run src/main.agi
agi run src/chain.agi
```

Continuous local beacon loop:

```bash
agi chain start --mode sbq-beacon --continuous
```

Bounded test run:

```bash
agi chain start --mode sbq-beacon --continuous --slot-seconds 1 --max-slots 3
```

Expected behavior: the command emits multiple JSON `slot` events and persists state to `storage/beacon.sqlite`.

## 5. Verify RPC stays running

```bash
agi chain rpc
```

Expected behavior: the process stays open until stopped manually.

## 6. Security checks included

This package includes regression tests for:

- encoded path traversal blocking;
- CGI path normalization;
- SQL identifier validation;
- unsafe migration definition blocking;
- AGILANG-native blockchain scaffold generation;
- continuous beacon loop persistence.

## Production boundary

This package is hardened for development, private-chain, and staging use. Public real-value operation still requires external audit, validator key-management review, RPC/P2P abuse testing, monitoring, backups, and long-running soak tests.
