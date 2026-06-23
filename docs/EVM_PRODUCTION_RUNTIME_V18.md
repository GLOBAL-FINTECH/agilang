# AGILANG v1.8 Production EVM Runtime

AGILANG v1.8 upgrades the EVM layer from ABI/helper tooling into an executable EVM toolkit.

## What is now implemented

- EVM bytecode interpreter
- Stack, memory, calldata, return data and storage models
- World-state simulator with accounts, code, balances and storage
- Opcode-level gas accounting
- Execution traces
- Logs/events via `LOG0` to `LOG4`
- `CALL`, `CALLCODE`, `DELEGATECALL`, `STATICCALL` simulation against local world state
- `CREATE` and `CREATE2` local account creation simulation
- `SLOAD`, `SSTORE`, `MLOAD`, `MSTORE`, `RETURN`, `REVERT`
- Rich ABI encoding and decoding for static and common dynamic types
- RLP transaction payload tooling
- JSON-RPC client helpers for chain calls
- External audited-engine bridge detection

## What this is not

This is not a complete Ethereum full node. It does not implement:

- peer-to-peer chain sync
- consensus validation
- fork-choice rules
- block production
- canonical chain database
- mempool management

For a regulated financial product or mainnet-critical blockchain system, connect AGILANG to an audited client or EVM implementation through `python_package()`, `native_library()`, or `evm_external_engine()`.

## AGILANG usage

```agi
fn main() -> i32:
    let code = "0x602a5f5260205ff3"
    let result = evm_execute(code)
    print(result["ok"])
    print(result["output"])
    return 0
```

## CLI usage

```bash
agi evm capabilities
agi evm run 0x600160020100
agi evm trace 0x600160020100
agi evm estimate-gas 0x600160020100
agi evm abi-encode string,uint256 agilang,7
agi evm abi-decode uint256 0x000000000000000000000000000000000000000000000000000000000000002a
agi evm unsigned-tx --nonce 1 --gas-price 10 --gas-limit 21000 --to 0x0000000000000000000000000000000000000001 --value 5 --chain-id 1
agi evm external-engine
```

## Recommended production architecture

```text
AGILANG EVM API
  -> built-in interpreter for deterministic local tests/simulation
  -> JSON-RPC for live chain reads/calls
  -> external audited engine bridge for consensus-grade execution
  -> native precompiled runtime path for performance-critical deployments
```

The design keeps AGILANG useful for developer tooling today while leaving a clean path to audited C/Rust/Go EVM engines for critical workloads.
