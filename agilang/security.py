"""AGILANG security helpers for web and realtime applications."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any, Callable

from .web import Request, Response, json_response


@dataclass
class SecurityConfig:
    csp: str = "default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    hsts: str = "max-age=31536000; includeSubDomains"
    referrer_policy: str = "strict-origin-when-cross-origin"
    permissions_policy: str = "camera=(), microphone=(), geolocation=()"
    max_body_bytes: int = 1024 * 1024
    rate_limit: int = 120
    rate_window_seconds: int = 60


class RateLimiter:
    """In-memory fixed-window rate limiter for local/server-process use."""

    def __init__(self, limit: int = 120, window_seconds: int = 60):
        self.limit = int(limit)
        self.window_seconds = int(window_seconds)
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.time()
        start = now - self.window_seconds
        hits = [t for t in self._hits.get(key, []) if t >= start]
        if len(hits) >= self.limit:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True


def security_config(**kwargs: Any) -> SecurityConfig:
    return SecurityConfig(**kwargs)


def security_headers(config: SecurityConfig | None = None) -> Callable[[Request, Response], Response]:
    cfg = config or SecurityConfig()
    def _after(request: Request, response: Response) -> Response:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", cfg.referrer_policy)
        response.headers.setdefault("Content-Security-Policy", cfg.csp)
        response.headers.setdefault("Permissions-Policy", cfg.permissions_policy)
        if request.headers.get("x-forwarded-proto", "").lower() == "https" or request.headers.get("x-forwarded-ssl", "").lower() == "on":
            response.headers.setdefault("Strict-Transport-Security", cfg.hsts)
        return response
    return _after


def body_limit(max_bytes: int = 1024 * 1024) -> Callable[[Request], Any]:
    def _middleware(request: Request) -> Any:
        if len(request.body or b"") > max_bytes:
            return json_response({"error": "Request body too large"}, status=413)
        return None
    return _middleware


def rate_limit(limit: int = 120, window_seconds: int = 60, key: Callable[[Request], str] | None = None) -> Callable[[Request], Any]:
    limiter = RateLimiter(limit, window_seconds)
    def _middleware(request: Request) -> Any:
        client_key = key(request) if key else (request.headers.get("x-forwarded-for") or (request.client[0] if request.client else "local"))
        if not limiter.allow(str(client_key)):
            return json_response({"error": "Too many requests"}, status=429, headers={"Retry-After": str(window_seconds)})
        return None
    return _middleware


def secure_random_token(bytes_len: int = 32) -> str:
    return secrets.token_urlsafe(bytes_len)


def constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(str(a), str(b))


def hmac_sign(message: str | bytes, secret: str | bytes) -> str:
    msg = message.encode("utf-8") if isinstance(message, str) else message
    sec = secret.encode("utf-8") if isinstance(secret, str) else secret
    return hmac.new(sec, msg, hashlib.sha256).hexdigest()


def hmac_verify(message: str | bytes, secret: str | bytes, signature: str) -> bool:
    return hmac.compare_digest(hmac_sign(message, secret), str(signature))


def api_key_hash(api_key: str, *, salt: str | None = None) -> str:
    salt = salt or base64.urlsafe_b64encode(os.urandom(16)).decode("ascii")
    digest = hashlib.pbkdf2_hmac("sha256", api_key.encode(), salt.encode(), 260000)
    return f"pbkdf2_sha256${salt}${base64.urlsafe_b64encode(digest).decode('ascii')}"


def verify_api_key(api_key: str, encoded: str) -> bool:
    try:
        alg, salt, _digest = encoded.split("$", 2)
    except ValueError:
        return False
    if alg != "pbkdf2_sha256":
        return False
    return hmac.compare_digest(api_key_hash(api_key, salt=salt), encoded)


__all__ = [
    "SecurityConfig", "RateLimiter", "security_config", "security_headers", "body_limit",
    "rate_limit", "secure_random_token", "constant_time_equal", "hmac_sign", "hmac_verify",
    "api_key_hash", "verify_api_key",
]
