# Validator Workflow

The unified in-house production profile uses built-in PoS validators plus SBQ beacon finality from JSON configuration.

## Key management

Use a private local validator key file:

```text
config/validator-keys.json
```

Reference it from the chain configuration:

```text
config/rpc.json -> chain.validator_signing_key_file
config/validators.json -> validator_signing_key_file
config/chain-services.json -> services.validator.key_file
```

Do not commit real validator keys to a public repository. Use an example file in GitHub and keep the real local file outside version control. For public or shared production, rotate local test keys and move signing into an audited controlled signer.

## Start command

```powershell
Set-Location C:\Users\user\smart-chain
$env:PYTHONPATH = "$PWD\vendor"
python -u scripts\run_chain.py --config config\chain-services.json
```

## One-cycle validation

```powershell
python -u scripts\run_chain.py --config config\chain-services.json --once
```
