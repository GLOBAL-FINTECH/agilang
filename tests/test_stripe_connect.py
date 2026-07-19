from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest

from agilang.stripe_connect import (
    StripeConfigurationError,
    StripeConnectConfig,
    StripeConnectGateway,
    StripeConnectStore,
    StripeHTTPClient,
    StripeWebhookError,
)


def config(tmp_path):
    return StripeConnectConfig(
        secret_key="sk_test_example",
        webhook_secret="whsec_example",
        api_base="https://api.stripe.com",
        database_path=str(tmp_path / "stripe.sqlite"),
    )


def signed(payload: bytes, secret: str, timestamp: int) -> str:
    digest = hmac.new(secret.encode(), str(timestamp).encode() + b"." + payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def test_config_rejects_unsafe_or_missing_keys(tmp_path):
    with pytest.raises(StripeConfigurationError):
        StripeConnectConfig(secret_key="bad", webhook_secret="whsec_ok", database_path=str(tmp_path / "x")).validate()
    with pytest.raises(StripeConfigurationError):
        StripeConnectConfig(secret_key="sk_test_ok", webhook_secret="bad", database_path=str(tmp_path / "x")).validate()
    with pytest.raises(StripeConfigurationError):
        StripeConnectConfig(secret_key="sk_test_ok", webhook_secret="whsec_ok", api_base="http://example.com").validate()


def test_nested_form_encoding():
    pairs = StripeHTTPClient._flatten({
        "amount": 1000,
        "automatic_payment_methods": {"enabled": True},
        "metadata": {"merchant_id": "m_1"},
        "expand": ["latest_charge", "customer"],
    })
    assert ("amount", "1000") in pairs
    assert ("automatic_payment_methods[enabled]", "true") in pairs
    assert ("metadata[merchant_id]", "m_1") in pairs
    assert ("expand[]", "latest_charge") in pairs


def test_idempotency_is_stable_and_operation_scoped(tmp_path):
    gateway = StripeConnectGateway(config(tmp_path))
    assert gateway.idempotency_key("payment", "order-1") == gateway.idempotency_key("payment", "order-1")
    assert gateway.idempotency_key("refund", "order-1") != gateway.idempotency_key("payment", "order-1")


def test_webhook_verification_and_deduplication(tmp_path):
    gateway = StripeConnectGateway(config(tmp_path))
    now = int(time.time())
    event = {
        "id": "evt_1",
        "type": "payment_intent.succeeded",
        "livemode": False,
        "data": {"object": {"id": "pi_1", "object": "payment_intent", "status": "succeeded", "amount": 5000, "currency": "usd"}},
    }
    payload = json.dumps(event, separators=(",", ":")).encode()
    signature = signed(payload, "whsec_example", now)
    assert gateway.verify_webhook(payload, signature, now=now)["id"] == "evt_1"
    first = gateway.handle_webhook(payload, signature)
    second = gateway.handle_webhook(payload, signature)
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    summary = gateway.admin_summary()
    assert summary["webhooks"]["processed"] == 1
    assert any(row["object_type"] == "payment_intent" for row in summary["objects"])


def test_webhook_rejects_bad_signature_and_old_timestamp(tmp_path):
    gateway = StripeConnectGateway(config(tmp_path))
    payload = b'{"id":"evt_bad","type":"account.updated"}'
    now = int(time.time())
    with pytest.raises(StripeWebhookError):
        gateway.verify_webhook(payload, f"t={now},v1=bad", now=now)
    old = now - gateway.config.webhook_tolerance_seconds - 1
    with pytest.raises(StripeWebhookError):
        gateway.verify_webhook(payload, signed(payload, "whsec_example", old), now=now)


def test_account_status_and_alerts(tmp_path):
    store = StripeConnectStore(str(tmp_path / "state.sqlite"))
    store.upsert_account({
        "id": "acct_1",
        "object": "account",
        "email": "merchant@example.com",
        "country": "US",
        "business_type": "company",
        "details_submitted": True,
        "charges_enabled": False,
        "payouts_enabled": False,
        "livemode": False,
        "metadata": {"merchant_id": "merchant-1"},
        "requirements": {"past_due": ["company.tax_id"], "disabled_reason": "requirements.past_due"},
        "capabilities": {"card_payments": "inactive", "transfers": "inactive"},
    })
    summary = store.admin_summary()
    assert summary["accounts"]["restricted"] == 1
    assert summary["alerts"]["critical"] == 1
    assert summary["alerts"]["high"] == 1


def test_payment_amount_validation(tmp_path):
    gateway = StripeConnectGateway(config(tmp_path))
    with pytest.raises(ValueError):
        gateway.create_destination_payment(
            merchant_id="m1", connected_account_id="acct_1", amount=100,
            currency="usd", application_fee_amount=100, payment_reference="order-1",
        )
