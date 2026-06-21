# AGILANG v1.6 EVM Tooling

AGILANG v1.6 includes EVM helper functions for blockchain tooling and smart-contract interaction.

## CLI

```bash
agi evm capabilities
agi evm selector 'transfer(address,uint256)'
agi evm calldata 'balanceOf(address)' --types address --values 0x0000000000000000000000000000000000000001
agi evm disasm 0x600160020100
agi evm build-demo
```

## AGILANG example

```agi
fn main() -> i32:
    let selector = evm_function_selector("transfer(address,uint256)")
    let call = evm_contract_call_data("balanceOf(address)", ["address"], ["0x0000000000000000000000000000000000000001"])
    let code = evm_bytecode_builder().push(1).push(2).add().stop().hex()
    print(selector)
    print(call)
    print(evm_disassemble(code))
    return 0
```

## Current scope

Included:

- selectors
- static ABI encoding
- call data generation
- bytecode builder
- disassembler
- JSON-RPC client

Not yet included:

- complete EVM interpreter
- Solidity compiler
- transaction signing
- account/key vault
- full Ethereum node

Those should be separate signed capability packs so the core language stays lean.
