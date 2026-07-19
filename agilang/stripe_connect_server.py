"""Runnable HTTP boundary for the AGILANG Stripe Connect gateway.

This is intentionally framework-neutral and standard-library-only. Production
installations should place it behind TLS, an authenticated reverse proxy, and a
process supervisor. The webhook endpoint remains unauthenticated because Stripe
HMAC verification authenticates the request.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .stripe_connect import StripeAPIError, StripeConnectError, StripeConnectGateway, StripeWebhookError


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


class StripeConnectHandler(BaseHTTPRequestHandler):
    gateway: StripeConnectGateway
    admin_token: str
    max_body_bytes = 2 * 1024 * 1024
    server_version = "AGILANGStripeConnect/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(json.dumps({"service": "stripe-connect", "remote": self.client_address[0], "message": fmt % args}))

    def _send(self, status: int, payload: Any, *, headers: dict[str, str] | None = None) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Correlation-ID", getattr(self, "correlation_id", ""))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if length < 0 or length > self.max_body_bytes:
            raise ValueError("request body exceeds limit")
        return self.rfile.read(length)

    def _json(self) -> dict[str, Any]:
        body = self._read_body()
        if not body:
            return {}
        value = json.loads(body.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object")
        return value

    def _admin_authorized(self) -> bool:
        supplied = self.headers.get("Authorization", "")
        return bool(self.admin_token) and secrets.compare_digest(supplied, f"Bearer {self.admin_token}")

    def _require_admin(self) -> bool:
        if self._admin_authorized():
            return True
        self._send(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "admin_authentication_required"})
        return False

    def _merchant_id(self) -> str:
        merchant_id = self.headers.get("X-AGILANG-Merchant-ID", "").strip()
        if not merchant_id or len(merchant_id) > 128 or not re.fullmatch(r"[A-Za-z0-9_.:@-]+", merchant_id):
            raise ValueError("a valid X-AGILANG-Merchant-ID header is required")
        return merchant_id

    def do_GET(self) -> None:
        self.correlation_id = self.headers.get("X-Correlation-ID") or secrets.token_hex(16)
        try:
            if self.path == "/health":
                self._send(HTTPStatus.OK, {"ok": True, "service": "agilang-stripe-connect", "capabilities": self.gateway.capabilities()})
                return
            if self.path == "/admin/summary":
                if not self._require_admin():
                    return
                self._send(HTTPStatus.OK, {"ok": True, "summary": self.gateway.admin_summary()})
                return
            match = re.fullmatch(r"/admin/accounts/(acct_[A-Za-z0-9]+)", self.path)
            if match:
                if not self._require_admin():
                    return
                account = self.gateway.retrieve_account(match.group(1))
                self._send(HTTPStatus.OK, {"ok": True, "account": account})
                return
            if self.path.startswith("/admin/disputes"):
                if not self._require_admin():
                    return
                self._send(HTTPStatus.OK, {"ok": True, "disputes": self.gateway.list_disputes(limit=100)})
                return
            self._send(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
        except Exception as exc:
            self._handle_error(exc)

    def do_POST(self) -> None:
        self.correlation_id = self.headers.get("X-Correlation-ID") or secrets.token_hex(16)
        try:
            if self.path == "/webhooks/stripe/connect":
                payload = self._read_body()
                signature = self.headers.get("Stripe-Signature", "")
                result = self.gateway.handle_webhook(payload, signature)
                self._send(HTTPStatus.OK, result)
                return

            if self.path == "/merchant/onboarding/account":
                merchant_id = self._merchant_id()
                data = self._json()
                account = self.gateway.create_connected_account(
                    merchant_id=merchant_id,
                    email=str(data["email"]),
                    country=str(data["country"]),
                    business_type=str(data.get("business_type", "company")),
                )
                self._send(HTTPStatus.CREATED, {"ok": True, "account": account})
                return

            if self.path == "/merchant/onboarding/link":
                self._merchant_id()
                data = self._json()
                link = self.gateway.create_account_link(
                    str(data["account_id"]), str(data["refresh_url"]), str(data["return_url"])
                )
                self._send(HTTPStatus.CREATED, {"ok": True, "onboarding": link})
                return

            if self.path == "/merchant/onboarding/session":
                self._merchant_id()
                data = self._json()
                session = self.gateway.create_account_session(str(data["account_id"]))
                self._send(HTTPStatus.CREATED, {"ok": True, "client_secret": session.get("client_secret")})
                return

            if self.path == "/merchant/payments":
                merchant_id = self._merchant_id()
                data = self._json()
                payment = self.gateway.create_destination_payment(
                    merchant_id=merchant_id,
                    connected_account_id=str(data["connected_account_id"]),
                    amount=int(data["amount"]),
                    currency=str(data["currency"]),
                    application_fee_amount=int(data.get("application_fee_amount", 0)),
                    payment_reference=str(data["payment_reference"]),
                    metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else None,
                    customer_id=str(data["customer_id"]) if data.get("customer_id") else None,
                )
                self._send(HTTPStatus.CREATED, {"ok": True, "payment": payment})
                return

            if self.path == "/merchant/refunds":
                self._merchant_id()
                data = self._json()
                refund = self.gateway.refund_payment(
                    str(data["payment_intent_id"]), refund_reference=str(data["refund_reference"]),
                    amount=int(data["amount"]) if data.get("amount") is not None else None,
                    refund_application_fee=bool(data.get("refund_application_fee", False)),
                    reverse_transfer=bool(data.get("reverse_transfer", False)),
                )
                self._send(HTTPStatus.CREATED, {"ok": True, "refund": refund})
                return

            if self.path == "/admin/reconcile/accounts":
                if not self._require_admin():
                    return
                data = self._json()
                account_ids = data.get("account_ids")
                if not isinstance(account_ids, list) or len(account_ids) > 100:
                    raise ValueError("account_ids must be an array containing no more than 100 IDs")
                self._send(HTTPStatus.OK, {"ok": True, "reconciliation": self.gateway.reconcile_accounts(map(str, account_ids))})
                return

            self._send(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
        except Exception as exc:
            self._handle_error(exc)

    def _handle_error(self, exc: Exception) -> None:
        if isinstance(exc, StripeWebhookError):
            self._send(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid_webhook", "message": str(exc)})
        elif isinstance(exc, StripeAPIError):
            status = HTTPStatus.BAD_GATEWAY if exc.status >= 500 or exc.status == 0 else HTTPStatus.UNPROCESSABLE_ENTITY
            self._send(status, {"ok": False, "error": "stripe_api_error", "message": str(exc), "stripe_status": exc.status,
                                "stripe_code": exc.code, "stripe_request_id": exc.request_id})
        elif isinstance(exc, (ValueError, KeyError, json.JSONDecodeError)):
            self._send(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid_request", "message": str(exc)})
        elif isinstance(exc, StripeConnectError):
            self._send(HTTPStatus.BAD_GATEWAY, {"ok": False, "error": "stripe_connect_error", "message": str(exc)})
        else:
            self.gateway.store.alert("critical", "HTTP_HANDLER_FAILURE", str(exc), resource_type="request", resource_id=self.path)
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": "internal_error", "correlation_id": self.correlation_id})


def serve(host: str = "127.0.0.1", port: int = 8787) -> None:
    gateway = StripeConnectGateway()
    admin_token = os.getenv("AGILANG_STRIPE_ADMIN_TOKEN", "")
    if len(admin_token) < 32:
        raise RuntimeError("AGILANG_STRIPE_ADMIN_TOKEN must contain at least 32 characters")
    handler = type("ConfiguredStripeConnectHandler", (StripeConnectHandler,), {"gateway": gateway, "admin_token": admin_token})
    server = ThreadingHTTPServer((host, int(port)), handler)
    print(json.dumps({"ok": True, "service": "agilang-stripe-connect", "host": host, "port": int(port)}))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m agilang.stripe_connect_server")
    parser.add_argument("--host", default=os.getenv("AGILANG_STRIPE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("AGILANG_STRIPE_PORT", "8787")))
    args = parser.parse_args(argv)
    serve(args.host, args.port)


if __name__ == "__main__":
    main()
