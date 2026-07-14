from agilang import rpc
from agilang.blockchain import blockchain_config


def _service():
    cfg = blockchain_config(
        chain_id=1923,
        strict_accounting=True,
        enforce_nonce_order=True,
        validators={"validator-1": 100},
        genesis_state={
            "balances": {"0x0000000000000000000000000000000000000001": 10**18},
            "contracts": {},
            "nonces": {},
        },
    )
    return rpc.make_rpc_service(cfg, db_path=":memory:")


def test_unsigned_transaction_methods_are_disabled():
    service = _service()
    for method in ("eth_sendTransaction", "dev_sendTransaction", "sbq_sendTransaction"):
        response = service.handle_one(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": [
                    {
                        "from": "0x0000000000000000000000000000000000000001",
                        "to": "0x0000000000000000000000000000000000000002",
                        "value": "0x1",
                    }
                ],
            }
        )
        assert response["error"]["code"] == -32000
        assert "eth_sendRawTransaction" in response["error"]["message"]


def test_contract_calls_fail_closed_instead_of_false_success():
    service = _service()
    call = service.handle_one(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "eth_call",
            "params": [
                {
                    "to": "0x0000000000000000000000000000000000000002",
                    "data": "0x",
                },
                "latest",
            ],
        }
    )
    estimate = service.handle_one(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "eth_estimateGas",
            "params": [{"to": "0x0000000000000000000000000000000000000002"}],
        }
    )
    assert call["error"]["code"] == -32601
    assert estimate["error"]["code"] == -32601
    assert call.get("result") is None
    assert estimate.get("result") is None


def test_jsonrpc_shape_and_batch_limits_are_enforced():
    service = _service()
    bad_version = service.handle_one(
        {"jsonrpc": "1.0", "id": 1, "method": "eth_chainId", "params": []}
    )
    bad_params = service.handle_one(
        {"jsonrpc": "2.0", "id": 2, "method": "eth_chainId", "params": {}}
    )
    oversized_batch = service.handle_many(
        [
            {"jsonrpc": "2.0", "id": i, "method": "eth_chainId", "params": []}
            for i in range(rpc.MAX_BATCH_SIZE + 1)
        ]
    )
    assert bad_version["error"]["code"] == -32600
    assert bad_params["error"]["code"] == -32602
    assert oversized_batch["error"]["code"] == -32600


def test_notification_returns_no_response():
    service = _service()
    assert (
        service.handle_one(
            {"jsonrpc": "2.0", "method": "web3_clientVersion", "params": []}
        )
        is None
    )


def test_txpool_content_is_not_public_by_default():
    service = _service()
    response = service.handle_one(
        {"jsonrpc": "2.0", "id": 4, "method": "txpool_content", "params": []}
    )
    assert response["error"]["code"] == -32000
