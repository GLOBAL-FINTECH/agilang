# Unified In-House Smart Chain Node

This profile starts the Smart Chain execution node, JSON-RPC endpoint, built-in validator producer, and SBQ beacon loop from JSON configuration.

It is not the dev profile. The default profile is `production` / `inhouse-production`.

## Main command

```powershell
Set-Location C:\Users\user\smart-chain
$env:PYTHONPATH = "$PWD\vendor"
python -u scripts\run_chain.py --config config\chain-services.json
```

Or on Windows:

```powershell
.\start-chain.ps1
```

## Dry-run validation

```powershell
python scripts\run_chain.py --config config\chain-services.json --dry-run
```

## Single-cycle test

```powershell
python scripts\run_chain.py --config config\chain-services.json --once
```

## JSON control

The service switchboard is `config/chain-services.json`.

- `services.node.enabled`: starts the execution node.
- `services.rpc.enabled`: starts JSON-RPC.
- `services.validator.enabled`: starts the in-house block producer.
- `services.beacon.enabled`: starts the SBQ beacon loop.
- `services.dev.enabled`: must remain false under production profile.

If a service is disabled, the unified starter does not start it.

## Production behavior

- RPC `auto_mine` is disabled in `config/rpc.json`.
- RPC `dev_send` is disabled in `config/rpc.json`.
- Transactions enter the shared node mempool.
- The in-house validator service produces canonical blocks.
- The beacon loop bridges execution payloads from the Smart Chain canonical head.

## Validator signing keys

Validator signing keys must be loaded from a private local file such as:

```text
config/validator-keys.json
```

Do not commit real validator keys to a public repository. Use `config/validator-keys.example.json` as the template and rotate keys before public/shared production deployment.
