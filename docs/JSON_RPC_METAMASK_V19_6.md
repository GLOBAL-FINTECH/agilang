# AGILANG v1.9.6 JSON-RPC + MetaMask Foundation

AGILANG v1.9.6 adds a dependency-light Ethereum-style JSON-RPC adapter for the blockchain framework.

## Start an SBQ-style local RPC server

```bash
agi blockchain rpc-server --config config/rpc.json --db storage/chain.sqlite --auto-mine --dev-send
```

Default local network values:

- RPC URL: `http://127.0.0.1:8545`
- Chain ID: `1900`
- Currency symbol: `SBQ`
- Decimals: `18`

## Implemented JSON-RPC methods

- `web3_clientVersion`
- `net_version`
- `net_listening`
- `net_peerCount`
- `eth_chainId`
- `eth_protocolVersion`
- `eth_syncing`
- `eth_mining`
- `eth_accounts`
- `eth_blockNumber`
- `eth_gasPrice`
- `eth_getBalance`
- `eth_getTransactionCount`
- `eth_getBlockByNumber`
- `eth_getBlockByHash`
- `eth_getTransactionByHash`
- `eth_getTransactionReceipt`
- `eth_getCode`
- `eth_estimateGas`
- `eth_call`
- `eth_sendRawTransaction` for AGILANG JSON transaction envelopes
- optional `eth_sendTransaction` for local development only

## Production boundary

MetaMask can add the network and read chain ID, height, balances and transaction receipts. Full real MetaMask transaction sending requires audited support for Ethereum signed raw transactions: RLP/EIP-1559 decoding, Keccak-256, and secp256k1 public key recovery. The built-in raw transaction handler intentionally rejects unknown signed raw transactions instead of pretending to validate them.
