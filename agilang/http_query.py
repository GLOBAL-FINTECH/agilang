"""HTTP query engine for AGILANG.

The module intentionally uses Python's standard library so the core AGILANG
runtime keeps a zero-dependency installation.  It exposes a small, predictable
request/response surface suitable for AGI bindings, Cloudflare Workers, REST
APIs, JSON endpoints, downloads, and form submissions.
"""
from __future__ import annotations

import json
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any, Mapping


class HTTPQueryError(RuntimeError):
    """Raised when an HTTP query cannot be completed safely."""


@dataclass(slots=True)
class HTTPResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    elapsed_ms: float

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    @property
    def text(self) -> str:
        content_type = self.headers.get("content-type", "")
        charset = "utf-8"
        for part in content_type.split(";"):
            part = part.strip()
            if part.lower().startswith("charset="):
                charset = part.split("=", 1)[1].strip() or "utf-8"
        return self.body.decode(charset, errors="replace")

    def json(self) -> Any:
        return json.loads(self.text)

    def as_dict(self, *, include_body: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "ok": self.ok,
            "status": self.status,
            "headers": dict(self.headers),
            "url": self.url,
            "elapsed_ms": self.elapsed_ms,
        }
        if include_body:
            result["body"] = self.text
            if "application/json" in self.headers.get("content-type", "").lower():
                try:
                    result["json"] = self.json()
                except json.JSONDecodeError:
                    result["json"] = None
        return result


class HTTPClient:
    """Small HTTP client with limits, retries, TLS, and SSRF protection.

    Private-network destinations are blocked by default.  Applications that
    deliberately call localhost services can opt in with allow_private=True.
    """

    def __init__(
        self,
        *,
        timeout: float = 20.0,
        max_response_bytes: int = 8 * 1024 * 1024,
        retries: int = 1,
        user_agent: str = "AGILANG-HTTP/2.1",
        allow_private: bool = False,
        verify_tls: bool = True,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be positive")
        if retries < 0:
            raise ValueError("retries cannot be negative")
        self.timeout = float(timeout)
        self.max_response_bytes = int(max_response_bytes)
        self.retries = int(retries)
        self.user_agent = str(user_agent)
        self.allow_private = bool(allow_private)
        self.verify_tls = bool(verify_tls)

    def get(self, url: str, *, params: Mapping[str, Any] | None = None, headers: Mapping[str, str] | None = None, **kwargs: Any) -> HTTPResponse:
        if params:
            query = urllib.parse.urlencode(params, doseq=True)
            separator = "&" if urllib.parse.urlsplit(url).query else "?"
            url = f"{url}{separator}{query}"
        return self.request("GET", url, headers=headers, **kwargs)

    def post(self, url: str, *, json_body: Any = None, form: Mapping[str, Any] | None = None, body: bytes | str | None = None, headers: Mapping[str, str] | None = None, **kwargs: Any) -> HTTPResponse:
        return self.request("POST", url, json_body=json_body, form=form, body=body, headers=headers, **kwargs)

    def put(self, url: str, **kwargs: Any) -> HTTPResponse:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> HTTPResponse:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> HTTPResponse:
        return self.request("DELETE", url, **kwargs)

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Any = None,
        form: Mapping[str, Any] | None = None,
        body: bytes | str | None = None,
        timeout: float | None = None,
        retries: int | None = None,
    ) -> HTTPResponse:
        method = method.upper().strip()
        if not method:
            raise ValueError("HTTP method is required")
        self._validate_url(url)

        supplied_bodies = sum(value is not None for value in (json_body, form, body))
        if supplied_bodies > 1:
            raise ValueError("use only one of json_body, form, or body")

        request_headers = {str(k): str(v) for k, v in (headers or {}).items()}
        request_headers.setdefault("User-Agent", self.user_agent)
        request_body: bytes | None = None
        if json_body is not None:
            request_body = json.dumps(json_body, separators=(",", ":")).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        elif form is not None:
            request_body = urllib.parse.urlencode(form, doseq=True).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        elif isinstance(body, str):
            request_body = body.encode("utf-8")
        elif body is not None:
            request_body = bytes(body)

        attempts = (self.retries if retries is None else int(retries)) + 1
        request_timeout = self.timeout if timeout is None else float(timeout)
        last_error: Exception | None = None

        for attempt in range(attempts):
            started = time.perf_counter()
            req = urllib.request.Request(url=url, data=request_body, headers=request_headers, method=method)
            try:
                context = ssl.create_default_context() if self.verify_tls else ssl._create_unverified_context()  # noqa: SLF001
                with urllib.request.urlopen(req, timeout=request_timeout, context=context) as response:
                    raw = response.read(self.max_response_bytes + 1)
                    if len(raw) > self.max_response_bytes:
                        raise HTTPQueryError(f"response exceeds {self.max_response_bytes} bytes")
                    elapsed = (time.perf_counter() - started) * 1000.0
                    return HTTPResponse(
                        status=int(response.status),
                        headers={k.lower(): v for k, v in response.headers.items()},
                        body=raw,
                        url=str(response.geturl()),
                        elapsed_ms=elapsed,
                    )
            except urllib.error.HTTPError as exc:
                raw = exc.read(self.max_response_bytes + 1)
                if len(raw) > self.max_response_bytes:
                    raise HTTPQueryError(f"response exceeds {self.max_response_bytes} bytes") from exc
                elapsed = (time.perf_counter() - started) * 1000.0
                response = HTTPResponse(
                    status=int(exc.code),
                    headers={k.lower(): v for k, v in exc.headers.items()},
                    body=raw,
                    url=str(exc.geturl()),
                    elapsed_ms=elapsed,
                )
                if exc.code < 500 or attempt + 1 >= attempts:
                    return response
                last_error = exc
            except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
                last_error = exc
                if attempt + 1 >= attempts:
                    break
            time.sleep(min(0.25 * (2**attempt), 2.0))

        raise HTTPQueryError(f"HTTP request failed after {attempts} attempt(s): {last_error}") from last_error

    def _validate_url(self, url: str) -> None:
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in {"http", "https"}:
            raise HTTPQueryError("only http and https URLs are supported")
        if not parts.hostname:
            raise HTTPQueryError("URL hostname is required")
        if self.allow_private:
            return
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM)}
        except socket.gaierror as exc:
            raise HTTPQueryError(f"cannot resolve hostname: {parts.hostname}") from exc
        for address in addresses:
            parsed = ip_address(address)
            if parsed.is_private or parsed.is_loopback or parsed.is_link_local or parsed.is_multicast or parsed.is_reserved or parsed.is_unspecified:
                raise HTTPQueryError(f"private or unsafe destination blocked: {address}")


def http_get(url: str, **kwargs: Any) -> dict[str, Any]:
    """AGI-friendly GET helper returning a plain dictionary."""
    return HTTPClient().get(url, **kwargs).as_dict()


def http_post(url: str, **kwargs: Any) -> dict[str, Any]:
    """AGI-friendly POST helper returning a plain dictionary."""
    return HTTPClient().post(url, **kwargs).as_dict()
