# EVM Chain Implementations Branch

Dedicated branch: `evm-chain-implementations`

The AGILANG repository keeps the stable runtime on `main`. EVM chain implementation work is separated into the `evm-chain-implementations` branch so JSON-RPC, MetaMask, SBQ/EVM, and wallet integration work can be developed without turning `main` into the experimental public-chain branch.

## Checkout

```bash
git fetch origin
git checkout evm-chain-implementations
```

## Use this branch for

- Ethereum-style JSON-RPC support
- MetaMask-compatible local network configuration
- SBQ/EVM chain implementation work
- wallet/app connectivity
- local RPC smoke tests
- EVM execution integration
- production hardening notes

## Keep `main` stable

The `main` branch remains the stable runtime branch. Mature EVM implementation work should move through:

```text
evm-chain-implementations → dev → main
```

## Related documentation

On the `evm-chain-implementations` branch, see:

- `docs/EVM_CHAIN_IMPLEMENTATIONS.md`
- `docs/JSON_RPC_METAMASK_V19_6.md`

## Local RPC target

```bash
agi blockchain rpc-server --config config/rpc.json --db storage/chain.sqlite --auto-mine --dev-send
```

Default local network target:

| Setting | Value |
|---|---|
| RPC URL | `http://127.0.0.1:8545` |
| Chain ID | `1900` |
| Currency symbol | `SBQ` |
| Decimals | `18` |
