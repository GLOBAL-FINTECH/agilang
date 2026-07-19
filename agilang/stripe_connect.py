"""Production-oriented Stripe Connect gateway for AGILANG.

The module uses only the Python standard library so AGILANG keeps zero mandatory
runtime dependencies. It provides secure Stripe REST transport, connected-account
onboarding, destination charges, refunds, transfers, payouts, disputes, webhook
verification, local monitoring state, audit logs, alerts, and reconciliation hooks.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


class StripeConnectError(RuntimeError):
    """Base Stripe Connect gateway error."""


class StripeConfigurationError(StripeConnectError):
    """Raised when required configuration is absent or unsafe."""


class StripeAPIError(StripeConnectError):
    """Raised when Stripe returns a non-success response."""

    def __init__(self, message: str, *, status: int = 0, code: str | None = None, request_id: str | None = None):
        super().__init__(message)
        self.status = int(status)
        self.code = code
        self.request_id = request_id


class StripeWebhookError(StripeConnectError):
    """Raised when webhook verification fails."""


@dataclass(frozen=True)
class StripeConnectConfig:
    secret_key: str
    webhook_secret: str
    publishable_key: str = ""
    api_base: str = "https://api.stripe.com"
    api_version: str | None = None
    timeout_seconds: int = 30
    webhook_tolerance_seconds: int = 300
    database_path: str = "storage/stripe-connect.sqlite"
    platform_name: str = "AGILANG Stripe Connect"

    @classmethod
    def from_env(cls) -> "StripeConnectConfig":
        return cls(
            secret_key=os.getenv("STRIPE_SECRET_KEY", ""),
            webhook_secret=os.getenv("STRIPE_CONNECT_WEBHOOK_SECRET", ""),
            publishable_key=os.getenv("STRIPE_PUBLISHABLE_KEY", ""),
            api_base=os.getenv("STRIPE_API_BASE", "https://api.stripe.com"),
            api_version=os.getenv("STRIPE_API_VERSION") or None,
            timeout_seconds=int(os.getenv("STRIPE_TIMEOUT_SECONDS", "30")),
            webhook_tolerance_seconds=int(os.getenv("STRIPE_WEBHOOK_TOLERANCE_SECONDS", "300")),
            database_path=os.getenv("STRIPE_CONNECT_DATABASE", "storage/stripe-connect.sqlite"),
            platform_name=os.getenv("STRIPE_PLATFORM_NAME", "AGILANG Stripe Connect"),
        )

    def validate(self) -> None:
        if not self.secret_key.startswith(("sk_test_", "sk_live_")):
            raise StripeConfigurationError("STRIPE_SECRET_KEY must be a Stripe secret key")
        if not self.webhook_secret.startswith("whsec_"):
            raise StripeConfigurationError("STRIPE_CONNECT_WEBHOOK_SECRET must begin with whsec_")
        if not self.api_base.startswith("https://") and "localhost" not in self.api_base and "127.0.0.1" not in self.api_base:
            raise StripeConfigurationError("Stripe API transport must use HTTPS")
        if self.timeout_seconds <= 0:
            raise StripeConfigurationError("timeout_seconds must be positive")


class StripeConnectStore:
    """SQLite-backed operational state and immutable-style audit history."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS connected_accounts (
                    stripe_account_id TEXT PRIMARY KEY,
                    merchant_id TEXT NOT NULL,
                    email TEXT,
                    country TEXT,
                    business_type TEXT,
                    details_submitted INTEGER NOT NULL DEFAULT 0,
                    charges_enabled INTEGER NOT NULL DEFAULT 0,
                    payouts_enabled INTEGER NOT NULL DEFAULT 0,
                    onboarding_status TEXT NOT NULL DEFAULT 'created',
                    disabled_reason TEXT,
                    requirements_json TEXT NOT NULL DEFAULT '{}',
                    capabilities_json TEXT NOT NULL DEFAULT '{}',
                    livemode INTEGER NOT NULL DEFAULT 0,
                    last_synced_at INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_connected_accounts_merchant ON connected_accounts(merchant_id);
                CREATE INDEX IF NOT EXISTS idx_connected_accounts_status ON connected_accounts(onboarding_status);

                CREATE TABLE IF NOT EXISTS stripe_objects (
                    object_id TEXT PRIMARY KEY,
                    object_type TEXT NOT NULL,
                    connected_account_id TEXT,
                    merchant_id TEXT,
                    status TEXT,
                    amount INTEGER,
                    currency TEXT,
                    payload_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_stripe_objects_type_status ON stripe_objects(object_type, status);
                CREATE INDEX IF NOT EXISTS idx_stripe_objects_account ON stripe_objects(connected_account_id);

                CREATE TABLE IF NOT EXISTS webhook_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    connected_account_id TEXT,
                    livemode INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    received_at INTEGER NOT NULL,
                    processed_at INTEGER
                );
                CREATE INDEX IF NOT EXISTS idx_webhook_status ON webhook_events(status, received_at);

                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    severity TEXT NOT NULL,
                    code TEXT NOT NULL,
                    message TEXT NOT NULL,
                    resource_type TEXT,
                    resource_id TEXT,
                    acknowledged INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_alerts_open ON alerts(acknowledged, severity, created_at);

                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_type TEXT NOT NULL,
                    actor_id TEXT,
                    action TEXT NOT NULL,
                    resource_type TEXT,
                    resource_id TEXT,
                    correlation_id TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_log(resource_type, resource_id, created_at);
                """
            )

    def audit(self, action: str, *, resource_type: str | None = None, resource_id: str | None = None,
              actor_type: str = "system", actor_id: str | None = None,
              correlation_id: str | None = None, metadata: Mapping[str, Any] | None = None) -> str:
        correlation_id = correlation_id or secrets.token_hex(16)
        with self.connect() as db:
            db.execute(
                "INSERT INTO audit_log(actor_type, actor_id, action, resource_type, resource_id, correlation_id, metadata_json, created_at) VALUES(?,?,?,?,?,?,?,?)",
                (actor_type, actor_id, action, resource_type, resource_id, correlation_id,
                 json.dumps(dict(metadata or {}), sort_keys=True), int(time.time())),
            )
        return correlation_id

    def alert(self, severity: str, code: str, message: str, *, resource_type: str | None = None,
              resource_id: str | None = None) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO alerts(severity, code, message, resource_type, resource_id, created_at) VALUES(?,?,?,?,?,?)",
                (severity, code, message, resource_type, resource_id, int(time.time())),
            )

    def upsert_account(self, account: Mapping[str, Any], merchant_id: str | None = None) -> None:
        account_id = str(account["id"])
        metadata = account.get("metadata") or {}
        merchant_id = merchant_id or str(metadata.get("merchant_id") or account_id)
        requirements = account.get("requirements") or {}
        capabilities = account.get("capabilities") or {}
        status = self._derive_onboarding_status(account)
        now = int(time.time())
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO connected_accounts(
                    stripe_account_id, merchant_id, email, country, business_type,
                    details_submitted, charges_enabled, payouts_enabled, onboarding_status,
                    disabled_reason, requirements_json, capabilities_json, livemode,
                    last_synced_at, created_at, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(stripe_account_id) DO UPDATE SET
                    merchant_id=excluded.merchant_id, email=excluded.email, country=excluded.country,
                    business_type=excluded.business_type, details_submitted=excluded.details_submitted,
                    charges_enabled=excluded.charges_enabled, payouts_enabled=excluded.payouts_enabled,
                    onboarding_status=excluded.onboarding_status, disabled_reason=excluded.disabled_reason,
                    requirements_json=excluded.requirements_json, capabilities_json=excluded.capabilities_json,
                    livemode=excluded.livemode, last_synced_at=excluded.last_synced_at, updated_at=excluded.updated_at
                """,
                (
                    account_id, merchant_id, account.get("email"), account.get("country"), account.get("business_type"),
                    int(bool(account.get("details_submitted"))), int(bool(account.get("charges_enabled"))),
                    int(bool(account.get("payouts_enabled"))), status, requirements.get("disabled_reason"),
                    json.dumps(requirements, sort_keys=True), json.dumps(capabilities, sort_keys=True),
                    int(bool(account.get("livemode"))), now, now, now,
                ),
            )
        if requirements.get("past_due"):
            self.alert("high", "ACCOUNT_REQUIREMENTS_PAST_DUE", "Connected account has past-due requirements",
                       resource_type="account", resource_id=account_id)
        if requirements.get("disabled_reason"):
            self.alert("critical", "ACCOUNT_RESTRICTED", str(requirements["disabled_reason"]),
                       resource_type="account", resource_id=account_id)

    @staticmethod
    def _derive_onboarding_status(account: Mapping[str, Any]) -> str:
        requirements = account.get("requirements") or {}
        if requirements.get("disabled_reason"):
            return "restricted"
        if requirements.get("pending_verification"):
            return "pending_verification"
        if requirements.get("currently_due") or requirements.get("past_due") or not account.get("details_submitted"):
            return "incomplete"
        if account.get("charges_enabled") and account.get("payouts_enabled"):
            return "active"
        return "submitted"

    def save_object(self, obj: Mapping[str, Any], *, connected_account_id: str | None = None,
                    merchant_id: str | None = None) -> None:
        object_id = str(obj["id"])
        object_type = str(obj.get("object") or "unknown")
        status = obj.get("status")
        amount = obj.get("amount")
        if amount is None:
            amount = obj.get("amount_received") or obj.get("amount_refunded")
        now = int(time.time())
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO stripe_objects(object_id, object_type, connected_account_id, merchant_id, status, amount, currency, payload_json, created_at, updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(object_id) DO UPDATE SET object_type=excluded.object_type,
                    connected_account_id=COALESCE(excluded.connected_account_id, stripe_objects.connected_account_id),
                    merchant_id=COALESCE(excluded.merchant_id, stripe_objects.merchant_id),
                    status=excluded.status, amount=excluded.amount, currency=excluded.currency,
                    payload_json=excluded.payload_json, updated_at=excluded.updated_at
                """,
                (object_id, object_type, connected_account_id, merchant_id, status, amount, obj.get("currency"),
                 json.dumps(dict(obj), sort_keys=True), now, now),
            )

    def register_event(self, event: Mapping[str, Any]) -> bool:
        now = int(time.time())
        try:
            with self.connect() as db:
                db.execute(
                    "INSERT INTO webhook_events(event_id, event_type, connected_account_id, livemode, payload_json, status, received_at) VALUES(?,?,?,?,?,'received',?)",
                    (event["id"], event["type"], event.get("account"), int(bool(event.get("livemode"))),
                     json.dumps(dict(event), sort_keys=True), now),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def mark_event(self, event_id: str, status: str, error_message: str | None = None) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE webhook_events SET status=?, attempts=attempts+1, error_message=?, processed_at=? WHERE event_id=?",
                (status, error_message, int(time.time()), event_id),
            )

    def admin_summary(self) -> dict[str, Any]:
        with self.connect() as db:
            account_rows = db.execute("SELECT onboarding_status, COUNT(*) AS n FROM connected_accounts GROUP BY onboarding_status").fetchall()
            object_rows = db.execute("SELECT object_type, status, COUNT(*) AS n, COALESCE(SUM(amount),0) AS amount FROM stripe_objects GROUP BY object_type, status").fetchall()
            events = db.execute("SELECT status, COUNT(*) AS n FROM webhook_events GROUP BY status").fetchall()
            open_alerts = db.execute("SELECT severity, COUNT(*) AS n FROM alerts WHERE acknowledged=0 GROUP BY severity").fetchall()
            oldest = db.execute("SELECT MIN(received_at) AS ts FROM webhook_events WHERE status IN ('received','failed')").fetchone()
        now = int(time.time())
        return {
            "accounts": {row["onboarding_status"]: row["n"] for row in account_rows},
            "objects": [dict(row) for row in object_rows],
            "webhooks": {row["status"]: row["n"] for row in events},
            "alerts": {row["severity"]: row["n"] for row in open_alerts},
            "oldest_unprocessed_webhook_seconds": max(0, now - oldest["ts"]) if oldest and oldest["ts"] else 0,
            "generated_at": now,
        }


class StripeHTTPClient:
    """Minimal Stripe REST client with idempotency, account scoping, and safe errors."""

    def __init__(self, config: StripeConnectConfig):
        config.validate()
        self.config = config

    @staticmethod
    def _flatten(data: Mapping[str, Any], prefix: str = "") -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        for key, value in data.items():
            name = f"{prefix}[{key}]" if prefix else str(key)
            if value is None:
                continue
            if isinstance(value, Mapping):
                pairs.extend(StripeHTTPClient._flatten(value, name))
            elif isinstance(value, (list, tuple)):
                for item in value:
                    pairs.append((f"{name}[]", str(item).lower() if isinstance(item, bool) else str(item)))
            elif isinstance(value, bool):
                pairs.append((name, str(value).lower()))
            else:
                pairs.append((name, str(value)))
        return pairs

    def request(self, method: str, path: str, *, data: Mapping[str, Any] | None = None,
                stripe_account: str | None = None, idempotency_key: str | None = None) -> dict[str, Any]:
        method = method.upper()
        body = None
        url = self.config.api_base.rstrip("/") + "/" + path.lstrip("/")
        encoded = urllib.parse.urlencode(self._flatten(data or {}), doseq=True)
        if method == "GET" and encoded:
            url += ("&" if "?" in url else "?") + encoded
        elif method != "GET":
            body = encoded.encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.config.secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "AGILANG-Stripe-Connect/1.0",
        }
        if self.config.api_version:
            headers["Stripe-Version"] = self.config.api_version
        if stripe_account:
            headers["Stripe-Account"] = stripe_account
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        request = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
                error = payload.get("error") or {}
                message = str(error.get("message") or raw)
                code = error.get("code")
            except json.JSONDecodeError:
                message, code = raw, None
            request_id = exc.headers.get("Request-Id") if exc.headers else None
            raise StripeAPIError(message, status=exc.code, code=code, request_id=request_id) from exc
        except urllib.error.URLError as exc:
            raise StripeAPIError(f"Stripe transport failure: {exc.reason}") from exc


class StripeConnectGateway:
    """High-level AGILANG Stripe Connect platform gateway."""

    def __init__(self, config: StripeConnectConfig | None = None):
        self.config = config or StripeConnectConfig.from_env()
        self.client = StripeHTTPClient(self.config)
        self.store = StripeConnectStore(self.config.database_path)

    @staticmethod
    def idempotency_key(operation: str, stable_reference: str) -> str:
        digest = hashlib.sha256(f"{operation}:{stable_reference}".encode()).hexdigest()
        return f"agi_{operation}_{digest[:32]}"

    def create_connected_account(self, merchant_id: str, email: str, country: str,
                                 *, business_type: str = "company") -> dict[str, Any]:
        data = {
            "type": "express",
            "country": country.upper(),
            "email": email,
            "business_type": business_type,
            "capabilities": {"card_payments": {"requested": True}, "transfers": {"requested": True}},
            "metadata": {"merchant_id": merchant_id, "platform": self.config.platform_name},
        }
        account = self.client.request("POST", "/v1/accounts", data=data,
                                      idempotency_key=self.idempotency_key("account", merchant_id))
        self.store.upsert_account(account, merchant_id)
        self.store.audit("stripe.account.created", resource_type="account", resource_id=account["id"],
                         metadata={"merchant_id": merchant_id, "country": country})
        return account

    def create_account_link(self, account_id: str, refresh_url: str, return_url: str) -> dict[str, Any]:
        return self.client.request("POST", "/v1/account_links", data={
            "account": account_id, "refresh_url": refresh_url, "return_url": return_url,
            "type": "account_onboarding",
        }, idempotency_key=self.idempotency_key("onboarding", f"{account_id}:{int(time.time()) // 300}"))

    def create_account_session(self, account_id: str) -> dict[str, Any]:
        components = {
            "account_onboarding": {"enabled": True},
            "account_management": {"enabled": True},
            "payments": {"enabled": True, "features": {
                "refund_management": True, "dispute_management": True, "capture_payments": True}},
            "balances": {"enabled": True},
            "payouts": {"enabled": True},
            "payouts_list": {"enabled": True},
            "disputes_list": {"enabled": True, "features": {"dispute_management": True}},
        }
        return self.client.request("POST", "/v1/account_sessions", data={"account": account_id, "components": components})

    def retrieve_account(self, account_id: str, *, merchant_id: str | None = None) -> dict[str, Any]:
        account = self.client.request("GET", f"/v1/accounts/{urllib.parse.quote(account_id)}")
        self.store.upsert_account(account, merchant_id)
        return account

    def create_destination_payment(self, *, merchant_id: str, connected_account_id: str,
                                   amount: int, currency: str, application_fee_amount: int,
                                   payment_reference: str, metadata: Mapping[str, Any] | None = None,
                                   customer_id: str | None = None) -> dict[str, Any]:
        if amount <= 0 or application_fee_amount < 0 or application_fee_amount >= amount:
            raise ValueError("amount must be positive and application fee must be between zero and amount")
        data: dict[str, Any] = {
            "amount": amount,
            "currency": currency.lower(),
            "automatic_payment_methods": {"enabled": True},
            "application_fee_amount": application_fee_amount,
            "transfer_data": {"destination": connected_account_id},
            "metadata": {"merchant_id": merchant_id, "payment_reference": payment_reference, **dict(metadata or {})},
        }
        if customer_id:
            data["customer"] = customer_id
        payment = self.client.request("POST", "/v1/payment_intents", data=data,
                                      idempotency_key=self.idempotency_key("payment", payment_reference))
        self.store.save_object(payment, connected_account_id=connected_account_id, merchant_id=merchant_id)
        self.store.audit("stripe.payment.created", resource_type="payment_intent", resource_id=payment["id"],
                         metadata={"merchant_id": merchant_id, "amount": amount, "currency": currency})
        return payment

    def refund_payment(self, payment_intent_id: str, *, refund_reference: str,
                       amount: int | None = None, refund_application_fee: bool = False,
                       reverse_transfer: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "payment_intent": payment_intent_id,
            "refund_application_fee": refund_application_fee,
            "reverse_transfer": reverse_transfer,
            "metadata": {"refund_reference": refund_reference},
        }
        if amount is not None:
            if amount <= 0:
                raise ValueError("refund amount must be positive")
            data["amount"] = amount
        refund = self.client.request("POST", "/v1/refunds", data=data,
                                     idempotency_key=self.idempotency_key("refund", refund_reference))
        self.store.save_object(refund)
        return refund

    def create_transfer(self, connected_account_id: str, amount: int, currency: str,
                        transfer_reference: str) -> dict[str, Any]:
        transfer = self.client.request("POST", "/v1/transfers", data={
            "destination": connected_account_id, "amount": amount, "currency": currency.lower(),
            "metadata": {"transfer_reference": transfer_reference},
        }, idempotency_key=self.idempotency_key("transfer", transfer_reference))
        self.store.save_object(transfer, connected_account_id=connected_account_id)
        return transfer

    def create_payout(self, connected_account_id: str, amount: int, currency: str,
                      payout_reference: str) -> dict[str, Any]:
        payout = self.client.request("POST", "/v1/payouts", stripe_account=connected_account_id, data={
            "amount": amount, "currency": currency.lower(), "metadata": {"payout_reference": payout_reference},
        }, idempotency_key=self.idempotency_key("payout", payout_reference))
        self.store.save_object(payout, connected_account_id=connected_account_id)
        return payout

    def list_disputes(self, *, connected_account_id: str | None = None, limit: int = 25) -> dict[str, Any]:
        return self.client.request("GET", "/v1/disputes", stripe_account=connected_account_id,
                                   data={"limit": max(1, min(int(limit), 100))})

    def verify_webhook(self, payload: bytes, stripe_signature: str, *, now: int | None = None) -> dict[str, Any]:
        fields: dict[str, list[str]] = {}
        for part in stripe_signature.split(","):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            fields.setdefault(key.strip(), []).append(value.strip())
        try:
            timestamp = int(fields["t"][0])
        except (KeyError, ValueError, IndexError) as exc:
            raise StripeWebhookError("Stripe-Signature is missing a valid timestamp") from exc
        current = int(time.time()) if now is None else int(now)
        if abs(current - timestamp) > self.config.webhook_tolerance_seconds:
            raise StripeWebhookError("Webhook timestamp is outside the configured tolerance")
        signed = str(timestamp).encode("ascii") + b"." + payload
        expected = hmac.new(self.config.webhook_secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
        if not any(hmac.compare_digest(expected, candidate) for candidate in fields.get("v1", [])):
            raise StripeWebhookError("Webhook signature verification failed")
        try:
            event = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StripeWebhookError("Webhook payload is not valid UTF-8 JSON") from exc
        if not isinstance(event, dict) or not event.get("id") or not event.get("type"):
            raise StripeWebhookError("Webhook event is missing id or type")
        return event

    def handle_webhook(self, payload: bytes, stripe_signature: str) -> dict[str, Any]:
        event = self.verify_webhook(payload, stripe_signature)
        if not self.store.register_event(event):
            return {"ok": True, "duplicate": True, "event_id": event["id"]}
        try:
            self._dispatch_event(event)
            self.store.mark_event(event["id"], "processed")
            return {"ok": True, "duplicate": False, "event_id": event["id"], "type": event["type"]}
        except Exception as exc:
            self.store.mark_event(event["id"], "failed", str(exc)[:1000])
            self.store.alert("critical", "WEBHOOK_PROCESSING_FAILED", str(exc), resource_type="webhook", resource_id=event["id"])
            raise

    def _dispatch_event(self, event: Mapping[str, Any]) -> None:
        event_type = str(event["type"])
        obj = ((event.get("data") or {}).get("object") or {})
        if not isinstance(obj, Mapping):
            return
        account_id = event.get("account")
        if event_type == "account.updated":
            self.store.upsert_account(obj)
        elif event_type.startswith(("payment_intent.", "charge.", "refund.", "transfer.", "payout.", "charge.dispute.")):
            self.store.save_object(obj, connected_account_id=str(account_id) if account_id else None)
        if event_type in {"payout.failed", "payment_intent.payment_failed", "charge.dispute.created"}:
            severity = "critical" if event_type == "charge.dispute.created" else "high"
            self.store.alert(severity, event_type.upper().replace(".", "_"), f"Stripe event requires attention: {event_type}",
                             resource_type=str(obj.get("object") or "stripe_object"), resource_id=str(obj.get("id") or ""))
        self.store.audit(f"stripe.webhook.{event_type}", resource_type=str(obj.get("object") or "event"),
                         resource_id=str(obj.get("id") or event["id"]), metadata={"event_id": event["id"]})

    def reconcile_accounts(self, account_ids: Iterable[str]) -> dict[str, Any]:
        results = {"ok": 0, "failed": 0, "errors": []}
        for account_id in account_ids:
            try:
                self.retrieve_account(account_id)
                results["ok"] += 1
            except StripeConnectError as exc:
                results["failed"] += 1
                results["errors"].append({"account_id": account_id, "error": str(exc)})
        return results

    def admin_summary(self) -> dict[str, Any]:
        return self.store.admin_summary()

    def capabilities(self) -> dict[str, Any]:
        return {
            "gateway": "stripe-connect",
            "version": "1.0",
            "account_model": "express",
            "onboarding": ["hosted", "embedded"],
            "payments": ["destination_charges", "application_fees"],
            "operations": ["accounts", "account_sessions", "payments", "refunds", "transfers", "payouts", "disputes", "webhooks", "reconciliation", "admin_monitoring"],
            "security": ["https", "secret_redaction", "idempotency", "hmac_webhooks", "timestamp_tolerance", "event_deduplication", "audit_log"],
            "config": asdict(self.config) | {"secret_key": "***", "webhook_secret": "***"},
        }
