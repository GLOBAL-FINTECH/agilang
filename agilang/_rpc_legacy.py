"""Ethereum-compatible JSON-RPC helpers for AGILANG blockchain nodes.

This module provides a dependency-light JSON-RPC service for private/staging
Smart Chain operation, including raw signed transaction decoding, txpool
visibility, nonce-aware submission, and optional local auto-mining for tests.
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from . import __version__
from .blockchain import BlockchainConfig, BlockchainNode, blockchain_config, blockchain_mainnet_config, blockchain_node, blockchain_transaction
from .evm import evm_keccak

JSONRPC_VERSION = "2.0"

_SECP256K1_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
_SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
_SECP256K1_GX = 55066263022277343669578718895168534326250603453777594175500187360389116729240
_SECP256K1_GY = 32670510020758816983085130507043184471273380659243275938904335757337482424
_SECP256K1_G = (_SECP256K1_GX, _SECP256K1_GY)


def _hex(value: Any) -> str:
    return hex(max(0, int(value or 0)))


def _parse_quantity(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    raw = str(value)
    if raw.startswith("0x"):
        return int(raw, 16)
    return int(raw)


def _strip_0x(value: str) -> str:
    return value[2:] if str(value).startswith("0x") else str(value)


def _keccak_bytes(data: bytes) -> bytes:
    return bytes.fromhex(_strip_0x(evm_keccak(data)))


def _int_to_bytes(value: int) -> bytes:
    value = int(value)
    if value == 0:
        return b""
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


def _bytes_to_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, bytes):
        return int.from_bytes(value, "big") if value else 0
    return _parse_quantity(value)


def _rlp_encode(value: Any) -> bytes:
    if isinstance(value, int):
        return _rlp_encode(_int_to_bytes(value))
    if isinstance(value, str):
        if value.startswith("0x"):
            return _rlp_encode(bytes.fromhex(_strip_0x(value)))
        return _rlp_encode(value.encode("utf-8"))
    if isinstance(value, bytes):
        if len(value) == 1 and value[0] < 0x80:
            return value
        if len(value) <= 55:
            return bytes([0x80 + len(value)]) + value
        length = _int_to_bytes(len(value))
        return bytes([0xB7 + len(length)]) + length + value
    if isinstance(value, (list, tuple)):
        payload = b"".join(_rlp_encode(item) for item in value)
        if len(payload) <= 55:
            return bytes([0xC0 + len(payload)]) + payload
        length = _int_to_bytes(len(payload))
        return bytes([0xF7 + len(length)]) + length + payload
    raise TypeError(f"unsupported RLP value type: {type(value).__name__}")


def _rlp_decode(data: bytes) -> Any:
    def decode_one(offset: int) -> Tuple[Any, int]:
        if offset >= len(data):
            raise ValueError("rlp_truncated")
        prefix = data[offset]
        if prefix < 0x80:
            return bytes([prefix]), offset + 1
        if prefix <= 0xB7:
            length = prefix - 0x80
            start = offset + 1
            end = start + length
            if end > len(data):
                raise ValueError("rlp_truncated_string")
            return data[start:end], end
        if prefix <= 0xBF:
            length_of_length = prefix - 0xB7
            start = offset + 1
            end = start + length_of_length
            if end > len(data):
                raise ValueError("rlp_truncated_long_string_length")
            length = int.from_bytes(data[start:end], "big")
            start = end
            end = start + length
            if end > len(data):
                raise ValueError("rlp_truncated_long_string")
            return data[start:end], end
        if prefix <= 0xF7:
            length = prefix - 0xC0
            start = offset + 1
            end = start + length
            if end > len(data):
                raise ValueError("rlp_truncated_list")
            items = []
            cursor = start
            while cursor < end:
                item, cursor = decode_one(cursor)
                items.append(item)
            return items, end
        length_of_length = prefix - 0xF7
        start = offset + 1
        end = start + length_of_length
        if end > len(data):
            raise ValueError("rlp_truncated_long_list_length")
        length = int.from_bytes(data[start:end], "big")
        start = end
        end = start + length
        if end > len(data):
            raise ValueError("rlp_truncated_long_list")
        items = []
        cursor = start
        while cursor < end:
            item, cursor = decode_one(cursor)
            items.append(item)
        return items, end

    decoded, pos = decode_one(0)
    if pos != len(data):
        raise ValueError("rlp_trailing_bytes")
    return decoded


def _ec_inv(value: int, modulus: int) -> int:
    return pow(value % modulus, -1, modulus)


def _ec_add(a: Tuple[int, int] | None, b: Tuple[int, int] | None) -> Tuple[int, int] | None:
    if a is None:
        return b
    if b is None:
        return a
    ax, ay = a
    bx, by = b
    if ax == bx and (ay + by) % _SECP256K1_P == 0:
        return None
    if a == b:
        slope = (3 * ax * ax) * _ec_inv(2 * ay, _SECP256K1_P) % _SECP256K1_P
    else:
        slope = (by - ay) * _ec_inv(bx - ax, _SECP256K1_P) % _SECP256K1_P
    x = (slope * slope - ax - bx) % _SECP256K1_P
    y = (slope * (ax - x) - ay) % _SECP256K1_P
    return (x, y)


def _ec_mul(k: int, point: Tuple[int, int] | None = _SECP256K1_G) -> Tuple[int, int] | None:
    k = int(k) % _SECP256K1_N
    result: Tuple[int, int] | None = None
    addend = point
    while k:
        if k & 1:
            result = _ec_add(result, addend)
        addend = _ec_add(addend, addend)
        k >>= 1
    return result


def _recover_public_key(message_hash: bytes, v_parity: int, r: int, s: int) -> Tuple[int, int]:
    if not (0 < r < _SECP256K1_N and 0 < s < _SECP256K1_N):
        raise ValueError("invalid_signature_rs_range")
    if s > _SECP256K1_N // 2:
        raise ValueError("invalid_signature_high_s")
    if v_parity not in (0, 1):
        raise ValueError("invalid_signature_y_parity")
    x = r
    alpha = (pow(x, 3, _SECP256K1_P) + 7) % _SECP256K1_P
    beta = pow(alpha, (_SECP256K1_P + 1) // 4, _SECP256K1_P)
    y = beta if (beta & 1) == v_parity else (_SECP256K1_P - beta)
    r_point = (x, y)
    z = int.from_bytes(message_hash, "big")
    r_inv = _ec_inv(r, _SECP256K1_N)
    s_r = _ec_mul(s, r_point)
    minus_z_g = _ec_mul((-z) % _SECP256K1_N, _SECP256K1_G)
    q = _ec_mul(r_inv, _ec_add(s_r, minus_z_g))
    if q is None:
        raise ValueError("signature_recovery_failed")
    return q


def _address_from_public_key(point: Tuple[int, int]) -> str:
    x, y = point
    pub = x.to_bytes(32, "big") + y.to_bytes(32, "big")
    return "0x" + _keccak_bytes(pub)[-20:].hex()


def _normalize_to_address(value: bytes) -> str:
    if not value:
        return ""
    if len(value) != 20:
        raise ValueError("invalid_to_address_length")
    return "0x" + value.hex()


def _tx_kind(to: str, data_hex: str) -> str:
    if not to and data_hex and data_hex != "0x":
        return "deploy_contract"
    if data_hex and data_hex != "0x":
        return "contract_call"
    return "transfer"


def _signing_test_vector_private_key_to_address(private_key: int) -> str:
    public_key = _ec_mul(private_key, _SECP256K1_G)
    if public_key is None:
        raise ValueError("invalid_private_key")
    return _address_from_public_key(public_key)


def _sign_hash_for_test_vector(message_hash: bytes, private_key: int) -> Tuple[int, int, int]:
    z = int.from_bytes(message_hash, "big")
    seed = int.from_bytes(_keccak_bytes(private_key.to_bytes(32, "big") + message_hash), "big")
    k = (seed % (_SECP256K1_N - 1)) + 1
    while True:
        point = _ec_mul(k, _SECP256K1_G)
        if point is None:
            k = (k + 1) % _SECP256K1_N
            continue
        r = point[0] % _SECP256K1_N
        if not r:
            k = (k + 1) % _SECP256K1_N
            continue
        s_sig = (_ec_inv(k, _SECP256K1_N) * (z + r * private_key)) % _SECP256K1_N
        if not s_sig:
            k = (k + 1) % _SECP256K1_N
            continue
        y_parity = point[1] & 1
        if s_sig > _SECP256K1_N // 2:
            s_sig = _SECP256K1_N - s_sig
            y_parity ^= 1
        return y_parity, r, s_sig


def _make_tx(sender: str, to: str, value: int, nonce_external: int, gas_limit: int, gas_price: int, data: bytes, raw_hash: str, family: str, chain_id: int, v: int, r: int, s: int, max_priority_fee_per_gas: int = 0, max_fee_per_gas: int = 0) -> Dict[str, Any]:
    data_hex = "0x" + bytes(data or b"").hex()
    tx = blockchain_transaction(
        sender=sender.lower(),
        to=to.lower(),
        value=value,
        data=data_hex,
        nonce=nonce_external,
        gas_limit=gas_limit,
        gas_price=gas_price,
        tx_type=_tx_kind(to, data_hex),
        signature=f"eth:{family}:v={v}:r={hex(r)}:s={hex(s)}",
        metadata={"rpc": True, "ethereum_raw": True, "ethereum_tx_type": family, "chain_id": int(chain_id), "external_nonce": int(nonce_external), "max_priority_fee_per_gas": int(max_priority_fee_per_gas), "max_fee_per_gas": int(max_fee_per_gas or gas_price)},
    )
    tx["hash"] = raw_hash
    return tx


def decode_ethereum_signed_raw_transaction(raw: str, expected_chain_id: int) -> Dict[str, Any]:
    raw_hex = _strip_0x(str(raw).strip())
    if not raw_hex or len(raw_hex) % 2:
        raise ValueError("invalid_signed_raw_transaction_hex")
    raw_bytes = bytes.fromhex(raw_hex)
    raw_hash = "0x" + _keccak_bytes(raw_bytes).hex()
    if raw_bytes[0] in (1, 2):
        tx_type = raw_bytes[0]
        fields = _rlp_decode(raw_bytes[1:])
        if tx_type == 1:
            if len(fields) != 11:
                raise ValueError("invalid_eip2930_field_count")
            chain_id = _bytes_to_int(fields[0]); nonce = _bytes_to_int(fields[1]); gas_price = _bytes_to_int(fields[2]); gas_limit = _bytes_to_int(fields[3]); to = _normalize_to_address(fields[4]); value = _bytes_to_int(fields[5]); data = fields[6]; y_parity = _bytes_to_int(fields[8]); r = _bytes_to_int(fields[9]); s_sig = _bytes_to_int(fields[10]); payload = bytes([tx_type]) + _rlp_encode(fields[:8]); family = "eip2930"; mp = 0; mf = gas_price
        else:
            if len(fields) != 12:
                raise ValueError("invalid_eip1559_field_count")
            chain_id = _bytes_to_int(fields[0]); nonce = _bytes_to_int(fields[1]); mp = _bytes_to_int(fields[2]); mf = _bytes_to_int(fields[3]); gas_price = mf; gas_limit = _bytes_to_int(fields[4]); to = _normalize_to_address(fields[5]); value = _bytes_to_int(fields[6]); data = fields[7]; y_parity = _bytes_to_int(fields[9]); r = _bytes_to_int(fields[10]); s_sig = _bytes_to_int(fields[11]); payload = bytes([tx_type]) + _rlp_encode(fields[:9]); family = "eip1559"
        if int(chain_id) != int(expected_chain_id):
            raise ValueError(f"wrong_chain_id_expected_{expected_chain_id}_got_{chain_id}")
        sender = _address_from_public_key(_recover_public_key(_keccak_bytes(payload), y_parity, r, s_sig))
        return _make_tx(sender, to, value, nonce, gas_limit, gas_price, data, raw_hash, family, chain_id, y_parity, r, s_sig, mp, mf)
    fields = _rlp_decode(raw_bytes)
    if not isinstance(fields, list) or len(fields) != 9:
        raise ValueError("invalid_legacy_field_count")
    nonce = _bytes_to_int(fields[0]); gas_price = _bytes_to_int(fields[1]); gas_limit = _bytes_to_int(fields[2]); to = _normalize_to_address(fields[3]); value = _bytes_to_int(fields[4]); data = fields[5]; v = _bytes_to_int(fields[6]); r = _bytes_to_int(fields[7]); s_sig = _bytes_to_int(fields[8])
    if v >= 35:
        chain_id = (v - 35) // 2
        y_parity = (v - 35) % 2
        signing_fields = fields[:6] + [_int_to_bytes(chain_id), b"", b""]
    elif v in (27, 28):
        chain_id = 0
        y_parity = v - 27
        signing_fields = fields[:6]
        if expected_chain_id:
            raise ValueError("missing_eip155_chain_id")
    else:
        raise ValueError("invalid_legacy_v")
    if int(chain_id) != int(expected_chain_id):
        raise ValueError(f"wrong_chain_id_expected_{expected_chain_id}_got_{chain_id}")
    sender = _address_from_public_key(_recover_public_key(_keccak_bytes(_rlp_encode(signing_fields)), y_parity, r, s_sig))
    return _make_tx(sender, to, value, nonce, gas_limit, gas_price, data, raw_hash, "legacy", chain_id, v, r, s_sig)


def _jsonrpc_result(request_id: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}


def _jsonrpc_error(request_id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
    err: Dict[str, Any] = {"jsonrpc": JSONRPC_VERSION, "id": request_id, "error": {"code": code, "message": message}}
    if data is not None:
        err["error"]["data"] = data
    return err


def _state(node: BlockchainNode) -> Dict[str, Any]:
    return node.db.all_state() if hasattr(node, "db") else {}


def _find_transaction(node: BlockchainNode, tx_hash: str):
    for block in node.canonical_chain():
        for idx, tx in enumerate(block.get("transactions") or []):
            if str(tx.get("hash")) == tx_hash:
                return block, tx, idx
    return None, None, None


def _find_receipt(node: BlockchainNode, tx_hash: str):
    for block in node.canonical_chain():
        for idx, receipt in enumerate(block.get("receipts") or []):
            if str(receipt.get("tx_hash")) == tx_hash:
                return block, receipt, idx
    return None, None, None


def _tx_to_rpc(tx: Dict[str, Any], block: Optional[Dict[str, Any]] = None, index: Optional[int] = None) -> Dict[str, Any]:
    meta = tx.get("metadata", {}) or {}
    ext_nonce = meta.get("external_nonce", tx.get("nonce", 0))
    family = str(meta.get("ethereum_tx_type", "legacy"))
    tx_type = "0x2" if family == "eip1559" else "0x1" if family == "eip2930" else "0x0"
    return {"hash": tx.get("hash"), "nonce": _hex(ext_nonce), "blockHash": block.get("hash") if block else None, "blockNumber": _hex(block.get("height", 0)) if block else None, "transactionIndex": _hex(index or 0) if block is not None else None, "from": tx.get("from"), "to": tx.get("to") or None, "value": _hex(tx.get("value", 0)), "gas": _hex(tx.get("gas_limit", 21000)), "gasPrice": _hex(tx.get("gas_price", 1)), "input": tx.get("data", "0x"), "type": tx_type, "chainId": _hex(meta.get("chain_id", getattr(block, "chain_id", 0)) or 0)}


def _receipt_to_rpc(block: Dict[str, Any], receipt: Dict[str, Any], index: int) -> Dict[str, Any]:
    tx_hash = str(receipt.get("tx_hash"))
    txs = block.get("transactions") or []
    tx = next((item for item in txs if str(item.get("hash")) == tx_hash), {})
    cumulative = sum(int(r.get("gas_used", 0)) for r in (block.get("receipts") or [])[: index + 1])
    return {"transactionHash": tx_hash, "transactionIndex": _hex(index), "blockHash": block.get("hash"), "blockNumber": _hex(block.get("height", 0)), "from": tx.get("from"), "to": tx.get("to") or None, "contractAddress": None, "cumulativeGasUsed": _hex(cumulative), "gasUsed": _hex(receipt.get("gas_used", 0)), "effectiveGasPrice": _hex(tx.get("gas_price", 1)), "logs": [], "logsBloom": "0x" + "0" * 512, "status": "0x1" if bool(receipt.get("ok", True)) else "0x0", "type": _tx_to_rpc(tx).get("type", "0x0")}


class EthJsonRpcService:
    def __init__(self, node: BlockchainNode, *, auto_mine: bool = False, expose_dev_send_transaction: bool = False) -> None:
        self.node = node
        self.auto_mine = bool(auto_mine)
        self.expose_dev_send_transaction = bool(expose_dev_send_transaction)

    def handle_many(self, payload: Any) -> Any:
        if isinstance(payload, list):
            return [self.handle_one(item) for item in payload]
        return self.handle_one(payload)

    def handle_one(self, request: Dict[str, Any]) -> Dict[str, Any]:
        request_id = request.get("id")
        try:
            return _jsonrpc_result(request_id, self.dispatch(str(request.get("method")), request.get("params") or []))
        except NotImplementedError as exc:
            return _jsonrpc_error(request_id, -32601, str(exc))
        except Exception as exc:
            return _jsonrpc_error(request_id, -32000, str(exc))

    def dispatch(self, method: str, params: List[Any]) -> Any:
        state = _state(self.node)
        if method == "web3_clientVersion": return f"AGILANG/{__version__}"
        if method == "eth_chainId": return _hex(self.node.config.chain_id)
        if method == "net_version": return str(self.node.config.chain_id)
        if method == "eth_blockNumber": return _hex(self.node.height())
        if method == "eth_gasPrice": return _hex(max(1, int(getattr(self.node.config, "mempool_min_gas_price", 1))))
        if method == "eth_maxPriorityFeePerGas": return _hex(1)
        if method == "eth_getBalance": return _hex((state.get("balances") or {}).get(str(params[0]).lower(), 0))
        if method == "eth_getTransactionCount": return _hex((state.get("nonces") or {}).get(str(params[0]).lower(), 0))
        if method == "eth_getCode": return (state.get("contracts") or {}).get(str(params[0]).lower(), "0x")
        if method == "eth_estimateGas": return _hex(21000)
        if method == "eth_call": return "0x"
        if method == "eth_getTransactionByHash":
            block, tx, index = _find_transaction(self.node, str(params[0])); return _tx_to_rpc(tx, block, index) if tx else None
        if method == "eth_getTransactionReceipt":
            block, receipt, index = _find_receipt(self.node, str(params[0])); return _receipt_to_rpc(block, receipt, index or 0) if block and receipt else None
        if method == "txpool_status":
            return {"pending": _hex(len(getattr(self.node.mempool, "ready_pool", {}))), "queued": _hex(len(getattr(self.node.mempool, "queued_pool", {})))}
        if method == "txpool_content":
            return {"pending": list(getattr(self.node.mempool, "ready_pool", {}).values()), "queued": list(getattr(self.node.mempool, "queued_pool", {}).values())}
        if method == "eth_sendRawTransaction":
            tx = decode_ethereum_signed_raw_transaction(str(params[0]), self.node.config.chain_id)
            added = self.node.submit_tx(tx)
            if not added.get("ok"):
                raise ValueError(json.dumps(added))
            if self.auto_mine:
                self._mine_pending()
            return added.get("hash") or tx.get("hash")
        if method in {"eth_sendTransaction", "dev_sendTransaction", "sbq_sendTransaction"}:
            if method == "dev_sendTransaction" and not self.expose_dev_send_transaction:
                raise PermissionError("dev_sendTransaction_disabled")
            p = dict(params[0] if params else {})
            sender = str(p.get("from", "")).lower()
            nonce = _parse_quantity(p.get("nonce"), (state.get("nonces") or {}).get(sender, 0))
            tx = blockchain_transaction(sender, str(p.get("to", "")).lower(), _parse_quantity(p.get("value", 0)), data=str(p.get("data", "0x")), nonce=nonce, gas_limit=_parse_quantity(p.get("gas", p.get("gasLimit", 21000))), gas_price=_parse_quantity(p.get("gasPrice", 1)))
            added = self.node.submit_tx(tx)
            if not added.get("ok"):
                raise ValueError(json.dumps(added))
            if self.auto_mine:
                self._mine_pending()
            return added.get("hash")
        raise NotImplementedError(f"unsupported JSON-RPC method: {method}")

    def _mine_pending(self) -> Optional[Dict[str, Any]]:
        last = None
        for _ in range(max(1, int(getattr(self.node.config, "max_block_txs", 1024)))):
            if self.node.mempool.size() <= 0 or not getattr(self.node.mempool, "ready_pool", {}):
                break
            parent = self.node.head(); slot = max(int(parent.get("slot", 0)) + 1, self.node._current_slot())
            proposer = self.node.consensus.select_proposer(parent["hash"], slot)
            last = self.node.produce_and_import_block(validator=proposer, slot=slot)
        return last


def make_rpc_service(config: BlockchainConfig | Dict[str, Any] | None = None, *, db_path: str | Path = ":memory:", auto_mine: bool = False, expose_dev_send_transaction: bool = False) -> EthJsonRpcService:
    return EthJsonRpcService(blockchain_node(config or blockchain_config(), db_path=db_path, node_id="rpc-node"), auto_mine=auto_mine, expose_dev_send_transaction=expose_dev_send_transaction)


def _load_json_file(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    data = json.loads(p.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _resolve_validator_signing_keys(config_path: str | Path, chain: Dict[str, Any]) -> Dict[str, str]:
    keys = dict(chain.get("validator_signing_keys", {}) or {})
    key_file = chain.get("validator_signing_key_file") or chain.get("validator_key_file")
    if key_file:
        base = Path(config_path).resolve().parent.parent
        key_path = base / str(key_file)
        if key_path.exists():
            data = _load_json_file(key_path)
            keys.update({str(k): str(v) for k, v in dict(data.get("validator_signing_keys", data.get("keys", {})) or {}).items() if str(v).strip()})
    missing = [addr for addr in dict(chain.get("validators", {}) or {}) if not str(keys.get(addr, "")).strip()]
    if bool(chain.get("require_block_signatures", False)) and missing:
        raise ValueError(f"missing validator signing keys for: {', '.join(missing)}")
    return keys


def node_from_rpc_config(path: str | Path, db_path: str | Path = ":memory:") -> BlockchainNode:
    data = _load_json_file(path)
    chain = data.get("chain", data)
    config_fn = blockchain_mainnet_config if bool(chain.get("mainnet_profile", data.get("mainnet_profile", True))) else blockchain_config
    cfg = config_fn(chain_id=int(chain.get("chain_id", 1900)), name=str(chain.get("name", "SBQ-Blockchain")), consensus_mode=str(chain.get("consensus", chain.get("consensus_mode", "pos"))), validators=dict(chain.get("validators", {})) or None, validator_signing_keys=_resolve_validator_signing_keys(path, chain), genesis_state=dict(chain.get("genesis_state", {})), mempool_min_gas_price=int(chain.get("mempool_min_gas_price", 1)), max_account_queue_gap=int(chain.get("max_account_queue_gap", 128)))
    return blockchain_node(cfg, db_path=db_path, node_id=str(data.get("node_id", "rpc-node")))


def serve_json_rpc(node: BlockchainNode, *, host: str = "127.0.0.1", port: int = 8545, auto_mine: bool = False, expose_dev_send_transaction: bool = False) -> None:
    service = EthJsonRpcService(node, auto_mine=auto_mine, expose_dev_send_transaction=expose_dev_send_transaction)

    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, status: int, payload: Any) -> None:
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Access-Control-Allow-Origin", "*"); self.send_header("Access-Control-Allow-Headers", "content-type"); self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS"); self.send_header("Content-Length", str(len(encoded))); self.end_headers(); self.wfile.write(encoded)
        def do_OPTIONS(self) -> None: self._send_json(200, {})
        def do_GET(self) -> None: self._send_json(200, {"ok": True, "client": f"AGILANG/{__version__}", "status": node.status()})
        def do_POST(self) -> None:
            try:
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))).decode("utf-8"))
                self._send_json(200, service.handle_many(payload))
            except Exception as exc:
                self._send_json(400, _jsonrpc_error(None, -32700, str(exc)))
        def log_message(self, format: str, *args: Any) -> None: return

    server = ThreadingHTTPServer((host, int(port)), Handler)
    print(f"AGILANG JSON-RPC listening on http://{host}:{port} chain_id={node.config.chain_id}")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AGILANG Ethereum JSON-RPC server")
    parser.add_argument("--host", default="127.0.0.1"); parser.add_argument("--port", type=int, default=8545); parser.add_argument("--db", default=".agilang/chain.sqlite"); parser.add_argument("--config", default=""); parser.add_argument("--auto-mine", action="store_true"); parser.add_argument("--dev-send", action="store_true")
    ns = parser.parse_args()
    node = node_from_rpc_config(ns.config, ns.db) if ns.config else blockchain_node(blockchain_mainnet_config(), db_path=ns.db, node_id="rpc-node")
    serve_json_rpc(node, host=ns.host, port=ns.port, auto_mine=ns.auto_mine, expose_dev_send_transaction=ns.dev_send)
