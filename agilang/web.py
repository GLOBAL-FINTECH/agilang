"""AGILANG web framework runtime.

This module provides a dependency-free HTTP framework for AGILANG's Python
backend. It is intentionally compact but practical: routing, route parameters,
request parsing, JSON/text/HTML responses, static files, simple templates,
secure-cookie helpers, password hashing helpers, an HTTP client for examples,
and a threaded development server.

Production note: the built-in server is suitable for development, local tools,
tests, prototypes, dashboards, and small internal services. For internet-facing
production deployment, place it behind a mature reverse proxy or adapt the app
through a production WSGI/ASGI bridge in a later AGILANG release.
"""

from __future__ import annotations

import base64
import contextlib
import email.utils
import hashlib
import hmac
import html
import json
import mimetypes
import os
import re
import secrets
import socket
import threading
import time
import queue
import uuid
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request as UrlRequest, urlopen

Handler = Callable[["Request"], Any]
Middleware = Callable[["Request"], Any]


class WebError(RuntimeError):
    """Base error for AGILANG web framework failures."""


class HTTPError(WebError):
    """Raise from route handlers to return a controlled HTTP error."""

    def __init__(self, status: int = 500, message: str | None = None, *, headers: Mapping[str, str] | None = None):
        self.status = int(status)
        self.message = message or HTTPStatus(self.status).phrase
        self.headers = dict(headers or {})
        super().__init__(f"HTTP {self.status}: {self.message}")


@dataclass
class Response:
    """HTTP response object returned by AGILANG route handlers."""

    body: str | bytes | dict[str, Any] | list[Any] | None = ""
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    content_type: str = "text/plain; charset=utf-8"

    def set_header(self, name: str, value: str) -> "Response":
        self.headers[name] = value
        return self

    def set_cookie(
        self,
        name: str,
        value: str,
        *,
        path: str = "/",
        max_age: int | None = None,
        http_only: bool = True,
        same_site: str = "Lax",
        secure: bool = False,
    ) -> "Response":
        parts = [f"{name}={quote(value)}", f"Path={path}"]
        if max_age is not None:
            parts.append(f"Max-Age={int(max_age)}")
        if http_only:
            parts.append("HttpOnly")
        if same_site:
            parts.append(f"SameSite={same_site}")
        if secure:
            parts.append("Secure")
        existing = self.headers.get("Set-Cookie")
        cookie = "; ".join(parts)
        self.headers["Set-Cookie"] = cookie if not existing else existing + ", " + cookie
        return self

    def to_bytes(self) -> bytes:
        if isinstance(self.body, bytes):
            return self.body
        if isinstance(self.body, (dict, list)):
            self.content_type = "application/json; charset=utf-8"
            return json.dumps(self.body, separators=(",", ":")).encode("utf-8")
        if self.body is None:
            return b""
        return str(self.body).encode("utf-8")


@dataclass
class Request:
    """HTTP request object passed to AGILANG route handlers."""

    method: str
    path: str
    query_string: str
    headers: dict[str, str]
    body: bytes
    params: dict[str, str] = field(default_factory=dict)
    client: tuple[str, int] | None = None

    @property
    def query(self) -> dict[str, str]:
        parsed = parse_qs(self.query_string, keep_blank_values=True)
        return {k: v[-1] if v else "" for k, v in parsed.items()}

    @property
    def query_all(self) -> dict[str, list[str]]:
        return parse_qs(self.query_string, keep_blank_values=True)

    @property
    def text(self) -> str:
        charset = "utf-8"
        content_type = self.headers.get("content-type", "")
        match = re.search(r"charset=([^;]+)", content_type, flags=re.I)
        if match:
            charset = match.group(1).strip()
        return self.body.decode(charset, errors="replace")

    def json(self, default: Any = None) -> Any:
        if not self.body:
            return default
        try:
            return json.loads(self.text)
        except json.JSONDecodeError:
            if default is not None:
                return default
            raise HTTPError(400, "Invalid JSON request body")

    @property
    def form(self) -> dict[str, str]:
        ctype = self.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" not in ctype:
            return {}
        parsed = parse_qs(self.text, keep_blank_values=True)
        return {k: v[-1] if v else "" for k, v in parsed.items()}

    @property
    def cookies(self) -> dict[str, str]:
        raw = self.headers.get("cookie", "")
        cookies: dict[str, str] = {}
        for part in raw.split(";"):
            if "=" in part:
                name, value = part.split("=", 1)
                cookies[name.strip()] = value.strip()
        return cookies

    def input(self, name: str, default: Any = None) -> Any:
        if name in self.params:
            return self.params[name]
        if name in self.query:
            return self.query[name]
        form = self.form
        if name in form:
            return form[name]
        payload = self.json(default={}) if self.headers.get("content-type", "").startswith("application/json") else {}
        if isinstance(payload, dict) and name in payload:
            return payload[name]
        return default


@dataclass
class Route:
    method: str
    path: str
    handler: Handler
    name: str | None = None
    middleware: list[Middleware] = field(default_factory=list)
    pattern: re.Pattern[str] | None = None
    param_names: list[str] = field(default_factory=list)

    @staticmethod
    def compile_path(path: str) -> tuple[re.Pattern[str], list[str]]:
        names: list[str] = []
        parts: list[str] = []
        for chunk in path.strip("/").split("/"):
            if not chunk:
                continue
            if chunk.startswith("<") and chunk.endswith(">"):
                name = chunk[1:-1].strip()
                names.append(name)
                parts.append(f"(?P<{name}>[^/]+)")
            else:
                parts.append(re.escape(chunk))
        pattern = "^/" + "/".join(parts) + "$"
        if path == "/":
            pattern = r"^/$"
        return re.compile(pattern), names

    def match(self, method: str, path: str) -> dict[str, str] | None:
        if self.method != method.upper() and self.method != "ANY":
            return None
        pattern = self.pattern
        if pattern is None:
            pattern, _ = self.compile_path(self.path)
            self.pattern = pattern
        m = pattern.match(path)
        if not m:
            return None
        return {k: v for k, v in m.groupdict().items()}


class WebApp:
    """Small AGILANG HTTP application with routing and middleware."""

    def __init__(self, *, name: str = "agilang", debug: bool = False):
        self.name = name
        self.debug = debug
        self.routes: list[Route] = []
        self.before_handlers: list[Callable[[Request], Any]] = []
        self.after_handlers: list[Callable[[Request, Response], Response | None]] = []
        self.static_mounts: list[tuple[str, Path]] = []
        self.middleware_groups: dict[str, list[Middleware]] = {}
        self._server: ThreadedWebServer | None = None

    def _resolve_middleware(self, middleware: str | Middleware | Sequence[str | Middleware] | None) -> list[Middleware]:
        if middleware is None:
            return []
        items: Sequence[str | Middleware]
        if isinstance(middleware, (str, bytes)) or callable(middleware):
            items = [middleware]  # type: ignore[list-item]
        else:
            items = list(middleware)
        resolved: list[Middleware] = []
        for item in items:
            if isinstance(item, str):
                if item not in self.middleware_groups:
                    raise KeyError(f"No middleware group named {item!r}")
                resolved.extend(self.middleware_groups[item])
            else:
                resolved.append(item)
        return resolved

    def route(
        self,
        method: str,
        path: str,
        handler: Handler,
        *,
        name: str | None = None,
        middleware: str | Middleware | Sequence[str | Middleware] | None = None,
    ) -> "WebApp":
        if not path.startswith("/"):
            path = "/" + path
        pattern, names = Route.compile_path(path)
        self.routes.append(Route(method.upper(), path, handler, name=name, middleware=self._resolve_middleware(middleware), pattern=pattern, param_names=names))
        return self

    def get(self, path: str, handler: Handler, *, name: str | None = None, middleware: str | Middleware | Sequence[str | Middleware] | None = None) -> "WebApp":
        return self.route("GET", path, handler, name=name, middleware=middleware)

    def post(self, path: str, handler: Handler, *, name: str | None = None, middleware: str | Middleware | Sequence[str | Middleware] | None = None) -> "WebApp":
        return self.route("POST", path, handler, name=name, middleware=middleware)

    def put(self, path: str, handler: Handler, *, name: str | None = None, middleware: str | Middleware | Sequence[str | Middleware] | None = None) -> "WebApp":
        return self.route("PUT", path, handler, name=name, middleware=middleware)

    def delete(self, path: str, handler: Handler, *, name: str | None = None, middleware: str | Middleware | Sequence[str | Middleware] | None = None) -> "WebApp":
        return self.route("DELETE", path, handler, name=name, middleware=middleware)

    def any(self, path: str, handler: Handler, *, name: str | None = None, middleware: str | Middleware | Sequence[str | Middleware] | None = None) -> "WebApp":
        return self.route("ANY", path, handler, name=name, middleware=middleware)

    def before(self, handler: Callable[[Request], Any]) -> "WebApp":
        self.before_handlers.append(handler)
        return self

    def middleware_group(self, name: str, handlers: Sequence[Middleware]) -> "WebApp":
        self.middleware_groups[name] = list(handlers)
        return self

    def use(self, name: str, *handlers: Middleware) -> "WebApp":
        self.middleware_groups[name] = list(handlers)
        return self

    def after(self, handler: Callable[[Request, Response], Response | None]) -> "WebApp":
        self.after_handlers.append(handler)
        return self

    def static(self, url_prefix: str, directory: str | Path) -> "WebApp":
        prefix = url_prefix.rstrip("/") or "/"
        if not prefix.startswith("/"):
            prefix = "/" + prefix
        self.static_mounts.append((prefix, Path(directory).resolve()))
        return self

    def url_for(self, name: str, **params: Any) -> str:
        for route in self.routes:
            if route.name == name:
                path = route.path
                for key, value in params.items():
                    path = path.replace(f"<{key}>", quote(str(value)))
                return path
        raise KeyError(f"No route named {name!r}")

    def handle(self, request: Request) -> Response:
        for maybe in self.before_handlers:
            result = maybe(request)
            if result is not None:
                return self._coerce_response(result)

        static_response = self._try_static(request)
        if static_response is not None:
            return static_response

        for route in self.routes:
            params = route.match(request.method, request.path)
            if params is None:
                continue
            request.params = params
            try:
                for middleware in route.middleware:
                    result = middleware(request)
                    if result is not None:
                        return self._coerce_response(result)
                response = self._coerce_response(route.handler(request))
            except HTTPError as exc:
                response = text_response(exc.message, status=exc.status, headers=exc.headers)
            except Exception as exc:
                if self.debug:
                    response = text_response(f"Internal Server Error\n{type(exc).__name__}: {exc}", status=500)
                else:
                    response = text_response("Internal Server Error", status=500)
            for after in self.after_handlers:
                replacement = after(request, response)
                if replacement is not None:
                    response = replacement
            return response

        return text_response("Not Found", status=404)

    def listen(self, host: str = "127.0.0.1", port: int = 0) -> "ThreadedWebServer":
        self._server = ThreadedWebServer(self, host, int(port))
        return self._server

    def run(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        self.listen(host, port).serve_forever()

    def _coerce_response(self, value: Any) -> Response:
        if isinstance(value, Response):
            return value
        if isinstance(value, (dict, list)):
            return json_response(value)
        if isinstance(value, bytes):
            return Response(value, content_type="application/octet-stream")
        return html_response(str(value))

    def _try_static(self, request: Request) -> Response | None:
        if request.method not in {"GET", "HEAD"}:
            return None
        for prefix, directory in self.static_mounts:
            if request.path == prefix or request.path.startswith(prefix + "/"):
                rel = request.path[len(prefix):].lstrip("/") or "index.html"
                candidate = (directory / rel).resolve()
                if directory not in candidate.parents and candidate != directory:
                    return text_response("Forbidden", status=403)
                if not candidate.exists() or not candidate.is_file():
                    return text_response("Not Found", status=404)
                return file_response(candidate)
        return None


class ThreadedWebServer:
    """Threaded development server returned by app.listen()."""

    def __init__(self, app: WebApp, host: str, port: int):
        self.app = app
        self.host = host
        self.port = int(port)
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def actual_port(self) -> int:
        if self._httpd is None:
            return self.port
        return int(self._httpd.server_address[1])

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.actual_port}"

    def run_background(self) -> "ThreadedWebServer":
        if self._thread and self._thread.is_alive():
            return self
        self._start_httpd()
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="agilang-web-server", daemon=True)
        self._thread.start()
        return self

    def serve_forever(self) -> None:
        self._start_httpd()
        self._httpd.serve_forever()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._thread and self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=1.0)

    def _start_httpd(self) -> None:
        if self._httpd is not None:
            return
        app = self.app

        class _Handler(BaseHTTPRequestHandler):
            server_version = "AGILANGWeb/0.9"
            sys_version = ""

            def do_GET(self): self._handle()
            def do_POST(self): self._handle()
            def do_PUT(self): self._handle()
            def do_DELETE(self): self._handle()
            def do_PATCH(self): self._handle()
            def do_HEAD(self): self._handle(head_only=True)
            def do_OPTIONS(self): self._handle()

            def log_message(self, fmt: str, *args: Any) -> None:
                if app.debug:
                    super().log_message(fmt, *args)

            def _handle(self, head_only: bool = False) -> None:
                parsed = urlparse(self.path)
                length = int(self.headers.get("content-length", "0") or "0")
                body = self.rfile.read(length) if length > 0 else b""
                req = Request(
                    method=self.command.upper(),
                    path=parsed.path or "/",
                    query_string=parsed.query,
                    headers={k.lower(): v for k, v in self.headers.items()},
                    body=body,
                    client=self.client_address,
                )
                resp = app.handle(req)
                payload = resp.to_bytes()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", resp.content_type))
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Date", email.utils.formatdate(usegmt=True))
                for name, value in resp.headers.items():
                    if name.lower() in {"content-type", "content-length", "date"}:
                        continue
                    self.send_header(name, value)
                self.end_headers()
                if not head_only:
                    self.wfile.write(payload)

        self._httpd = ThreadingHTTPServer((self.host, self.port), _Handler)


def web_app(name: str = "agilang", debug: bool = False) -> WebApp:
    """Create an AGILANG web application."""

    return WebApp(name=name, debug=debug)


def text_response(text: str, *, status: int = 200, headers: Mapping[str, str] | None = None) -> Response:
    return Response(text, status=status, headers=dict(headers or {}), content_type="text/plain; charset=utf-8")


def html_response(html_text: str, *, status: int = 200, headers: Mapping[str, str] | None = None) -> Response:
    return Response(html_text, status=status, headers=dict(headers or {}), content_type="text/html; charset=utf-8")


def json_response(data: Any, *, status: int = 200, headers: Mapping[str, str] | None = None) -> Response:
    return Response(data, status=status, headers=dict(headers or {}), content_type="application/json; charset=utf-8")


def redirect(location: str, *, status: int = 302) -> Response:
    return Response("", status=status, headers={"Location": location}, content_type="text/plain; charset=utf-8")


def file_response(path: str | Path, *, download_name: str | None = None) -> Response:
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise HTTPError(404, "File not found")
    content_type = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
    headers: dict[str, str] = {}
    if download_name:
        headers["Content-Disposition"] = f'attachment; filename="{download_name}"'
    return Response(p.read_bytes(), headers=headers, content_type=content_type)


def _template_lookup(data: Mapping[str, Any], key: str) -> Any:
    value: Any = data
    for part in key.split("."):
        part = part.strip()
        if part == "":
            return ""
        if isinstance(value, Mapping):
            value = value.get(part, "")
        else:
            value = getattr(value, part, "")
    return value


def render_template(template: str | Path, context: Mapping[str, Any] | None = None, **kwargs: Any) -> str:
    """Render a tiny HTML template with {{ name }} placeholders.

    Values are HTML-escaped by default. Use triple braces {{{ raw }}} for trusted
    raw HTML. This is intentionally small; complex apps should plug in a richer
    engine later.
    """

    data: dict[str, Any] = dict(context or {})
    data.update(kwargs)
    template_text = str(template)
    looks_inline = "\n" in template_text or "{{" in template_text or "<" in template_text
    if not looks_inline:
        try:
            candidate = Path(template_text)
            source = candidate.read_text(encoding="utf-8") if candidate.exists() else template_text
        except OSError:
            source = template_text
    else:
        source = template_text

    def raw_replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        return str(_template_lookup(data, key))

    def escaped_replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        return html.escape(str(_template_lookup(data, key)))

    source = re.sub(r"\{\{\{\s*([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\}\}\}", raw_replace, source)
    source = re.sub(r"\{\{\s*([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\}\}", escaped_replace, source)
    return source


def _attrs(raw: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in re.finditer(r"([A-Za-z_][\w:-]*)\s*=\s*\"([^\"]*)\"", raw)}


def seo_tags(meta: Mapping[str, Any] | None = None, **kwargs: Any) -> str:
    """Render SEO, Open Graph, Twitter, canonical, and robots tags.

    Supported keys: title, description, canonical, image, type, site_name,
    robots, locale, twitter_card, author, keywords, and json_ld.
    """

    data: dict[str, Any] = dict(meta or {})
    data.update(kwargs)
    title = str(data.get("title", "") or "")
    description = str(data.get("description", "") or "")
    canonical = str(data.get("canonical", "") or "")
    image = str(data.get("image", "") or "")
    page_type = str(data.get("type", "website") or "website")
    site_name = str(data.get("site_name", "") or "")
    robots = str(data.get("robots", "index,follow") or "index,follow")
    locale = str(data.get("locale", "") or "")
    twitter_card = str(data.get("twitter_card", "summary_large_image") or "summary_large_image")
    author = str(data.get("author", "") or "")
    keywords = str(data.get("keywords", "") or "")
    json_ld = data.get("json_ld")

    tags: list[str] = []
    if description:
        tags.append(f'<meta name="description" content="{html.escape(description, quote=True)}">')
    if canonical:
        tags.append(f'<link rel="canonical" href="{html.escape(canonical, quote=True)}">')
    if robots:
        tags.append(f'<meta name="robots" content="{html.escape(robots, quote=True)}">')
    if author:
        tags.append(f'<meta name="author" content="{html.escape(author, quote=True)}">')
    if keywords:
        tags.append(f'<meta name="keywords" content="{html.escape(keywords, quote=True)}">')
    if title:
        tags.append(f'<meta property="og:title" content="{html.escape(title, quote=True)}">')
    if description:
        tags.append(f'<meta property="og:description" content="{html.escape(description, quote=True)}">')
    if canonical:
        tags.append(f'<meta property="og:url" content="{html.escape(canonical, quote=True)}">')
    tags.append(f'<meta property="og:type" content="{html.escape(page_type, quote=True)}">')
    if site_name:
        tags.append(f'<meta property="og:site_name" content="{html.escape(site_name, quote=True)}">')
    if locale:
        tags.append(f'<meta property="og:locale" content="{html.escape(locale, quote=True)}">')
    if image:
        tags.append(f'<meta property="og:image" content="{html.escape(image, quote=True)}">')
    tags.append(f'<meta name="twitter:card" content="{html.escape(twitter_card, quote=True)}">')
    if title:
        tags.append(f'<meta name="twitter:title" content="{html.escape(title, quote=True)}">')
    if description:
        tags.append(f'<meta name="twitter:description" content="{html.escape(description, quote=True)}">')
    if image:
        tags.append(f'<meta name="twitter:image" content="{html.escape(image, quote=True)}">')
    if json_ld:
        payload = json.dumps(json_ld, separators=(",", ":")) if not isinstance(json_ld, str) else json_ld
        tags.append(f'<script type="application/ld+json">{html.escape(payload, quote=False)}</script>')
    return "\n  ".join(tags)


def render_ags(template: str | Path, context: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Render an AGILANG Single-file View (.ags) into body + page metadata.

    This first AGS foundation supports HTML-like markup, dotted {{ values }},
    triple-brace raw HTML, and @page metadata. Reactive @fetch/@live directives
    are preserved as metadata for the browser runtime/build tools to consume.
    """

    data: dict[str, Any] = dict(context or {})
    data.update(kwargs)
    path = Path(template)
    source = path.read_text(encoding="utf-8") if path.exists() else str(template)
    meta: dict[str, Any] = {}
    fetches: list[dict[str, str]] = []
    lives: list[dict[str, str]] = []
    body_lines: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("@page"):
            attrs = _attrs(stripped[len("@page"):])
            meta.update(attrs)
            if "seo_description" in attrs and "description" not in meta:
                meta["description"] = attrs["seo_description"]
            continue
        if stripped.startswith("@layout"):
            meta["layout"] = stripped[len("@layout"):].strip().strip('"')
            continue
        if stripped.startswith("@fetch"):
            match = re.match(r"@fetch\s+([A-Za-z_]\w*)\s+from\s+\"([^\"]+)\"", stripped)
            if match:
                fetches.append({"name": match.group(1), "url": match.group(2)})
            continue
        if stripped.startswith("@live"):
            match = re.match(r"@live\s+([A-Za-z_]\w*)\s+from\s+\"([^\"]+)\"(?:\s+every\s+(\d+))?", stripped)
            if match:
                lives.append({"name": match.group(1), "url": match.group(2), "every": match.group(3) or ""})
            continue
        if stripped.startswith("@state"):
            continue
        body_lines.append(line)
    body_source = "\n".join(body_lines)

    # Automatic AGS reactive bindings. A page can declare:
    #   @live stats from "/api/home-stats" every 5000
    # and then write normal template expressions such as:
    #   {{ stats.users }}
    # AGILANG renders a browser-bound span that ags-runtime.js hydrates
    # without requiring the developer to hand-write data-ags-live attributes.
    live_by_name = {item["name"]: item for item in lives}
    fetch_by_name = {item["name"]: item for item in fetches}

    def bind_replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        if "." not in key:
            return match.group(0)
        root_name, path_name = key.split(".", 1)
        if root_name in live_by_name:
            cfg = live_by_name[root_name]
            url = html.escape(str(cfg.get("url", "")), quote=True)
            every = html.escape(str(cfg.get("every") or "5000"), quote=True)
            path_attr = html.escape(path_name, quote=True)
            return f'<span data-ags-live="{url}" data-ags-path="{path_attr}" data-ags-every="{every}"></span>'
        if root_name in fetch_by_name:
            cfg = fetch_by_name[root_name]
            url = html.escape(str(cfg.get("url", "")), quote=True)
            path_attr = html.escape(path_name, quote=True)
            return f'<span data-ags-fetch="{url}" data-ags-path="{path_attr}"></span>'
        return match.group(0)

    body_source = re.sub(r"\{\{\s*([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)\s*\}\}", bind_replace, body_source)
    body = render_template(body_source, data)
    meta["fetches"] = fetches
    meta["lives"] = lives
    return {"body": body, "meta": meta, "seo": seo_tags(meta)}


def web_get(url: str, *, timeout: float = 5.0, headers: Mapping[str, str] | None = None) -> str:
    req = UrlRequest(url, headers=dict(headers or {}), method="GET")
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def web_post_json(url: str, payload: Any, *, timeout: float = 5.0, headers: Mapping[str, str] | None = None) -> str:
    data = json.dumps(payload).encode("utf-8")
    final_headers = {"Content-Type": "application/json"}
    final_headers.update(dict(headers or {}))
    req = UrlRequest(url, data=data, headers=final_headers, method="POST")
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def hash_password(password: str, *, iterations: int = 260_000) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256$%d$%s$%s" % (
        iterations,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_s, salt_s, digest_s = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        salt = base64.b64decode(salt_s)
        expected = base64.b64decode(digest_s)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def sign_cookie(data: Mapping[str, Any], secret: str, *, max_age: int | None = None) -> str:
    payload = {"data": dict(data), "iat": int(time.time()), "max_age": max_age}
    raw = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii").rstrip("=")
    sig = hmac.new(secret.encode("utf-8"), raw.encode("ascii"), hashlib.sha256).hexdigest()
    return raw + "." + sig


def verify_cookie(token: str, secret: str) -> dict[str, Any] | None:
    try:
        raw, sig = token.rsplit(".", 1)
        expected = hmac.new(secret.encode("utf-8"), raw.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        padded = raw + "=" * (-len(raw) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        max_age = payload.get("max_age")
        if max_age is not None and int(time.time()) - int(payload.get("iat", 0)) > int(max_age):
            return None
        return dict(payload.get("data", {}))
    except Exception:
        return None


class SQLiteDB:
    """Tiny sqlite helper for AGILANG web apps."""

    def __init__(self, path: str | Path):
        self.path = str(path)

    @contextlib.contextmanager
    def connect(self):
        import sqlite3
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def execute(self, sql: str, params: Iterable[Any] = ()) -> int:
        with self.connect() as conn:
            cur = conn.execute(sql, tuple(params))
            return cur.rowcount

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        with self.connect() as conn:
            cur = conn.execute(sql, tuple(params))
            return [dict(row) for row in cur.fetchall()]

    def one(self, sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None


def sqlite_db(path: str | Path) -> SQLiteDB:
    return SQLiteDB(path)


class MySQLDB:
    """Tiny MySQL helper with the same API as SQLiteDB."""

    def __init__(self, *, host: str = "127.0.0.1", port: int = 3306, user: str = "root", password: str = "", database: str = "", charset: str = "utf8mb4"):
        self.config = {
            "host": host,
            "port": int(port),
            "user": user,
            "password": password,
            "database": database,
            "charset": charset,
        }

    @contextlib.contextmanager
    def connect(self):
        try:
            import pymysql
            from pymysql.cursors import DictCursor
            conn = pymysql.connect(cursorclass=DictCursor, autocommit=False, **self.config)
        except ImportError:
            try:
                import mysql.connector
                conn = mysql.connector.connect(**self.config)
            except ImportError as exc:
                raise ImportError("Install PyMySQL or mysql-connector-python to use mysql_db().") from exc
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _sql(self, sql: str) -> str:
        return sql.replace("?", "%s")

    def execute(self, sql: str, params: Iterable[Any] = ()) -> int:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(self._sql(sql), tuple(params))
            rowcount = cur.rowcount
            cur.close()
            return rowcount

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        with self.connect() as conn:
            try:
                cur = conn.cursor(dictionary=True)
            except TypeError:
                cur = conn.cursor()
            cur.execute(self._sql(sql), tuple(params))
            rows = cur.fetchall()
            cur.close()
            return [dict(row) for row in rows]

    def one(self, sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None


def mysql_db(*, host: str = "127.0.0.1", port: int = 3306, user: str = "root", password: str = "", database: str = "", charset: str = "utf8mb4") -> MySQLDB:
    return MySQLDB(host=host, port=port, user=user, password=password, database=database, charset=charset)


# --- v0.9 full web platform additions: ORM, migrations, validation, auth, CSRF, jobs, adapters ---

class Field:
    """SQLite-backed ORM field descriptor."""

    def __init__(self, column_type: str = "TEXT", *, primary_key: bool = False, default: Any = None, nullable: bool = True, unique: bool = False):
        self.column_type = column_type.upper()
        self.primary_key = primary_key
        self.default = default
        self.nullable = nullable
        self.unique = unique

    def ddl(self, name: str) -> str:
        parts = [name, self.column_type]
        if self.primary_key:
            parts.append("PRIMARY KEY")
        if not self.nullable and not self.primary_key:
            parts.append("NOT NULL")
        if self.unique:
            parts.append("UNIQUE")
        return " ".join(parts)


def string(default: str | None = None, *, nullable: bool = True, unique: bool = False) -> Field:
    return Field("TEXT", default=default, nullable=nullable, unique=unique)


def integer(default: int | None = None, *, primary_key: bool = False, nullable: bool = True, unique: bool = False) -> Field:
    return Field("INTEGER", primary_key=primary_key, default=default, nullable=nullable, unique=unique)


def real(default: float | None = None, *, nullable: bool = True) -> Field:
    return Field("REAL", default=default, nullable=nullable)


def boolean(default: bool | None = None, *, nullable: bool = True) -> Field:
    return Field("INTEGER", default=default, nullable=nullable)


class ModelMeta(type):
    def __new__(mcls, name, bases, namespace):
        fields: dict[str, Field] = {}
        for base in bases:
            fields.update(getattr(base, "__fields__", {}))
        for key, value in list(namespace.items()):
            if isinstance(value, Field):
                fields[key] = value
                namespace.pop(key)
        cls = super().__new__(mcls, name, bases, namespace)
        cls.__fields__ = fields
        if not getattr(cls, "__table__", None):
            cls.__table__ = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower() + "s"
        return cls


class QuerySet:
    def __init__(self, model_cls: type["Model"], db: SQLiteDB, where_sql: str = "", params: Sequence[Any] = ()): 
        self.model_cls = model_cls
        self.db = db
        self.where_sql = where_sql
        self.params = tuple(params)

    def all(self) -> list["Model"]:
        sql = f"SELECT * FROM {self.model_cls.__table__}"
        if self.where_sql:
            sql += " WHERE " + self.where_sql
        return [self.model_cls(**row) for row in self.db.query(sql, self.params)]

    def first(self) -> "Model" | None:
        sql = f"SELECT * FROM {self.model_cls.__table__}"
        if self.where_sql:
            sql += " WHERE " + self.where_sql
        row = self.db.one(sql + " LIMIT 1", self.params)
        return self.model_cls(**row) if row else None


class Model(metaclass=ModelMeta):
    """Tiny active-record style SQLite model base."""

    __table__: str = ""
    __fields__: dict[str, Field] = {}
    id = Field("INTEGER", primary_key=True, nullable=False)

    def __init__(self, **values: Any):
        for name, field in self.__fields__.items():
            setattr(self, name, values.get(name, field.default() if callable(field.default) else field.default))

    @classmethod
    def create_table(cls, db: SQLiteDB) -> None:
        ddl = ", ".join(field.ddl(name) for name, field in cls.__fields__.items())
        db.execute(f"CREATE TABLE IF NOT EXISTS {cls.__table__} ({ddl})")

    @classmethod
    def objects(cls, db: SQLiteDB) -> QuerySet:
        return QuerySet(cls, db)

    @classmethod
    def where(cls, db: SQLiteDB, **filters: Any) -> QuerySet:
        clauses = [f"{key} = ?" for key in filters]
        return QuerySet(cls, db, " AND ".join(clauses), tuple(filters.values()))

    @classmethod
    def get(cls, db: SQLiteDB, id: Any) -> "Model" | None:
        return cls.where(db, id=id).first()

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name, None) for name in self.__fields__}

    def save(self, db: SQLiteDB) -> "Model":
        fields = [name for name in self.__fields__ if not (name == "id" and getattr(self, name, None) in (None, 0))]
        values = [getattr(self, name, None) for name in fields]
        if getattr(self, "id", None):
            update_fields = [name for name in fields if name != "id"]
            assignments = ", ".join(f"{name} = ?" for name in update_fields)
            db.execute(f"UPDATE {self.__table__} SET {assignments} WHERE id = ?", [getattr(self, n, None) for n in update_fields] + [self.id])
        else:
            placeholders = ", ".join("?" for _ in fields)
            with db.connect() as conn:
                cur = conn.execute(f"INSERT INTO {self.__table__} ({', '.join(fields)}) VALUES ({placeholders})", values)
                if "id" in self.__fields__:
                    self.id = cur.lastrowid
        return self

    def delete(self, db: SQLiteDB) -> int:
        if not getattr(self, "id", None):
            return 0
        return db.execute(f"DELETE FROM {self.__table__} WHERE id = ?", [self.id])


def model(name: str, fields: Mapping[str, Field], *, table: str | None = None) -> type[Model]:
    """Create an AGILANG model class dynamically from a field mapping."""
    namespace: dict[str, Any] = {"__table__": table or name.lower() + "s"}
    namespace.update(dict(fields))
    return type(name, (Model,), namespace)


class MigrationManager:
    def __init__(self, db: SQLiteDB):
        self.db = db
        self.db.execute("CREATE TABLE IF NOT EXISTS agilang_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")

    def applied(self) -> set[str]:
        return {row["name"] for row in self.db.query("SELECT name FROM agilang_migrations")}

    def apply(self, name: str, fn: Callable[[SQLiteDB], Any]) -> bool:
        if name in self.applied():
            return False
        fn(self.db)
        self.db.execute("INSERT INTO agilang_migrations (name, applied_at) VALUES (?, ?)", [name, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())])
        return True

    def run(self, migrations: Sequence[tuple[str, Callable[[SQLiteDB], Any]]]) -> list[str]:
        applied: list[str] = []
        for name, fn in migrations:
            if self.apply(name, fn):
                applied.append(name)
        return applied


def migrate(db: SQLiteDB, migrations: Sequence[tuple[str, Callable[[SQLiteDB], Any]]]) -> list[str]:
    return MigrationManager(db).run(migrations)


class ValidationResult:
    def __init__(self, ok: bool, errors: dict[str, list[str]], data: dict[str, Any]):
        self.ok = ok
        self.errors = errors
        self.data = data

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": self.errors, "data": self.data}


def _rule_list(rules: str | Sequence[str]) -> list[str]:
    if isinstance(rules, str):
        return [r.strip() for r in rules.split("|") if r.strip()]
    return [str(r) for r in rules]


def validate(data: Mapping[str, Any], schema: Mapping[str, str | Sequence[str]]) -> ValidationResult:
    errors: dict[str, list[str]] = {}
    clean: dict[str, Any] = dict(data)
    for field_name, raw_rules in schema.items():
        value = data.get(field_name)
        for rule in _rule_list(raw_rules):
            name, _, arg = rule.partition(":")
            if name == "required" and (value is None or value == ""):
                errors.setdefault(field_name, []).append("required")
            elif name == "email" and value not in (None, "") and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(value)):
                errors.setdefault(field_name, []).append("email")
            elif name == "min" and value not in (None, "") and len(str(value)) < int(arg or 0):
                errors.setdefault(field_name, []).append(f"min:{arg}")
            elif name == "max" and value not in (None, "") and len(str(value)) > int(arg or 0):
                errors.setdefault(field_name, []).append(f"max:{arg}")
            elif name == "int" and value not in (None, ""):
                try:
                    clean[field_name] = int(value)
                except Exception:
                    errors.setdefault(field_name, []).append("int")
            elif name == "number" and value not in (None, ""):
                try:
                    clean[field_name] = float(value)
                except Exception:
                    errors.setdefault(field_name, []).append("number")
            elif name.startswith("in") and arg:
                allowed = [x.strip() for x in arg.split(",")]
                if str(value) not in allowed:
                    errors.setdefault(field_name, []).append(rule)
    return ValidationResult(not errors, errors, clean)


def validation_middleware(schema: Mapping[str, str | Sequence[str]]) -> Middleware:
    def _middleware(request: Request) -> Any:
        payload = request.json(default={}) if request.headers.get("content-type", "").startswith("application/json") else {**request.query, **request.form}
        result = validate(payload, schema)
        request.validation = result  # type: ignore[attr-defined]
        if not result.ok:
            return json_response({"errors": result.errors}, status=422)
        request.validated = result.data  # type: ignore[attr-defined]
        return None
    return _middleware


def csrf_token(secret: str, session_id: str | None = None) -> str:
    session_id = session_id or secrets.token_hex(16)
    return sign_cookie({"sid": session_id, "nonce": secrets.token_hex(16)}, secret, max_age=3600)


def csrf_input(token: str) -> str:
    return f'<input type="hidden" name="_csrf" value="{html.escape(token)}">'


def csrf_protect(secret: str, *, methods: Sequence[str] = ("POST", "PUT", "PATCH", "DELETE")) -> Middleware:
    unsafe = {m.upper() for m in methods}
    def _middleware(request: Request) -> Any:
        if request.method.upper() not in unsafe:
            return None
        supplied = request.headers.get("x-csrf-token") or request.form.get("_csrf") or (request.json(default={}) or {}).get("_csrf")
        if not supplied or verify_cookie(str(supplied), secret) is None:
            return json_response({"error": "CSRF token missing or invalid"}, status=403)
        return None
    return _middleware


def login_user(response: Response, user: Mapping[str, Any], secret: str, *, cookie_name: str = "agi_session", max_age: int = 86400) -> Response:
    token = sign_cookie({"user": dict(user)}, secret, max_age=max_age)
    response.set_cookie(cookie_name, token, max_age=max_age)
    return response


def current_user(request: Request, secret: str, *, cookie_name: str = "agi_session") -> dict[str, Any] | None:
    token = request.cookies.get(cookie_name)
    if not token:
        return None
    data = verify_cookie(token, secret)
    if not data:
        return None
    user = data.get("user")
    return dict(user) if isinstance(user, Mapping) else None


def logout_user(response: Response, *, cookie_name: str = "agi_session") -> Response:
    response.set_cookie(cookie_name, "", max_age=0)
    return response


def auth_required(secret: str, *, cookie_name: str = "agi_session", redirect_to: str | None = None) -> Middleware:
    def _middleware(request: Request) -> Any:
        user = current_user(request, secret, cookie_name=cookie_name)
        if user is None:
            if redirect_to:
                return redirect(redirect_to)
            return json_response({"error": "Authentication required"}, status=401)
        request.user = user  # type: ignore[attr-defined]
        return None
    return _middleware


class Job:
    def __init__(self, func: Callable[..., Any], args: Sequence[Any], kwargs: Mapping[str, Any]):
        self.id = str(uuid.uuid4())
        self.func = func
        self.args = tuple(args)
        self.kwargs = dict(kwargs)
        self.status = "queued"
        self.result: Any = None
        self.error: str | None = None
        self.created_at = time.time()
        self.finished_at: float | None = None


class JobQueue:
    """Small in-process background job queue."""

    def __init__(self, workers: int = 1):
        self.jobs: dict[str, Job] = {}
        self._queue: queue.Queue[Job | None] = queue.Queue()
        self._threads: list[threading.Thread] = []
        self.workers = int(workers)
        self._started = False

    def start(self) -> "JobQueue":
        if self._started:
            return self
        self._started = True
        for i in range(max(1, self.workers)):
            t = threading.Thread(target=self._worker, name=f"agilang-job-worker-{i}", daemon=True)
            t.start()
            self._threads.append(t)
        return self

    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        self.start()
        job = Job(func, args, kwargs)
        self.jobs[job.id] = job
        self._queue.put(job)
        return job.id

    def status(self, job_id: str) -> dict[str, Any]:
        job = self.jobs[job_id]
        return {"id": job.id, "status": job.status, "result": job.result, "error": job.error, "created_at": job.created_at, "finished_at": job.finished_at}

    def stop(self) -> None:
        for _ in self._threads:
            self._queue.put(None)
        for t in self._threads:
            t.join(timeout=1.0)

    def _worker(self) -> None:
        while True:
            job = self._queue.get()
            if job is None:
                return
            try:
                job.status = "running"
                job.result = job.func(*job.args, **job.kwargs)
                job.status = "done"
            except Exception as exc:
                job.status = "failed"
                job.error = f"{type(exc).__name__}: {exc}"
            finally:
                job.finished_at = time.time()
                self._queue.task_done()


def job_queue(workers: int = 1) -> JobQueue:
    return JobQueue(workers=workers)


def wsgi_adapter(app: WebApp):
    """Return a PEP 3333 WSGI callable for production servers such as Gunicorn/uWSGI."""
    def _wsgi(environ, start_response):
        path = environ.get("PATH_INFO", "/") or "/"
        query = environ.get("QUERY_STRING", "")
        method = environ.get("REQUEST_METHOD", "GET").upper()
        length = int(environ.get("CONTENT_LENGTH") or "0")
        body = environ["wsgi.input"].read(length) if length else b""
        headers = {k[5:].replace("_", "-").lower(): v for k, v in environ.items() if k.startswith("HTTP_")}
        if environ.get("CONTENT_TYPE"):
            headers["content-type"] = environ["CONTENT_TYPE"]
        req = Request(method=method, path=path, query_string=query, headers=headers, body=body)
        resp = app.handle(req)
        payload = resp.to_bytes()
        status = f"{resp.status} {HTTPStatus(resp.status).phrase}"
        response_headers = [("Content-Type", resp.headers.get("Content-Type", resp.content_type)), ("Content-Length", str(len(payload)))]
        for k, v in resp.headers.items():
            if k.lower() not in {"content-type", "content-length"}:
                response_headers.append((k, v))
        start_response(status, response_headers)
        return [payload]
    return _wsgi


def asgi_adapter(app: WebApp):
    """Return a minimal ASGI HTTP callable for Uvicorn/Hypercorn style servers."""
    async def _asgi(scope, receive, send):
        if scope.get("type") != "http":
            raise RuntimeError("AGILANG ASGI adapter currently supports HTTP scope only")
        body_chunks: list[bytes] = []
        more = True
        while more:
            message = await receive()
            body_chunks.append(message.get("body", b""))
            more = message.get("more_body", False)
        headers = {k.decode("latin1").lower(): v.decode("latin1") for k, v in scope.get("headers", [])}
        req = Request(method=scope.get("method", "GET"), path=scope.get("path", "/"), query_string=scope.get("query_string", b"").decode("latin1"), headers=headers, body=b"".join(body_chunks))
        resp = app.handle(req)
        payload = resp.to_bytes()
        raw_headers = [(b"content-type", resp.headers.get("Content-Type", resp.content_type).encode("latin1")), (b"content-length", str(len(payload)).encode("latin1"))]
        for k, v in resp.headers.items():
            if k.lower() not in {"content-type", "content-length"}:
                raw_headers.append((k.lower().encode("latin1"), str(v).encode("latin1")))
        await send({"type": "http.response.start", "status": resp.status, "headers": raw_headers})
        await send({"type": "http.response.body", "body": payload})
    return _asgi


__all__ = [
    "HTTPError",
    "Request",
    "Response",
    "SQLiteDB",
    "MySQLDB",
    "ThreadedWebServer",
    "WebApp",
    "WebError",
    "file_response",
    "hash_password",
    "html_response",
    "json_response",
    "redirect",
    "render_ags",
    "seo_tags",
    "render_template",
    "sign_cookie",
    "sqlite_db",
    "mysql_db",
    "text_response",
    "verify_cookie",
    "verify_password",
    "web_app",
    "web_get",
    "web_post_json",
    "Field",
    "JobQueue",
    "MigrationManager",
    "Model",
    "ValidationResult",
    "asgi_adapter",
    "auth_required",
    "boolean",
    "csrf_input",
    "csrf_protect",
    "csrf_token",
    "current_user",
    "integer",
    "job_queue",
    "login_user",
    "logout_user",
    "migrate",
    "model",
    "real",
    "string",
    "validate",
    "validation_middleware",
    "wsgi_adapter",
]
