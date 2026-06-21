"""CGI/FastCGI shared-hosting runtime for AGILANG.

Adds classic CGI, optional FastCGI, and WSGI/Passenger bridges for cPanel and
Plesk-style hosting where apps are loaded like PHP front controllers.
"""
from __future__ import annotations

import os
import platform
import sys
import textwrap
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from .std import load_std_globals
from .translator import AGILTranslator
from .web import Request, Response, WebApp, text_response, wsgi_adapter


@dataclass
class HostingScaffoldResult:
    root: Path
    target: Path
    files: list[Path]
    mode: str
    def as_dict(self) -> dict[str, Any]:
        return {"root": str(self.root), "target": str(self.target), "mode": self.mode, "files": [str(f) for f in self.files]}


def resolve_entry(source_file: str | Path | None = None) -> Path:
    raw = source_file or os.environ.get("AGILANG_APP_ENTRY") or "src/main.agi"
    path = Path(raw).expanduser()
    if not path.is_absolute():
        project_root = Path(os.environ.get("AGILANG_PROJECT_ROOT", Path.cwd())).expanduser().resolve()
        path = project_root / path
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"AGILANG CGI entry file not found: {path}")
    if path.suffix != ".agi":
        raise ValueError(f"AGILANG CGI entry must be a .agi file: {path}")
    return path


def load_agilang_web_app(source_file: str | Path | None = None) -> WebApp:
    source_path = resolve_entry(source_file)
    python_code = AGILTranslator().translate_file(source_path)
    exec_globals = load_std_globals()
    builtins_obj = __builtins__
    exec_globals.update(builtins_obj if isinstance(builtins_obj, dict) else vars(builtins_obj))
    exec_globals["__name__"] = "__agilang_cgi_app__"
    exec_globals["__file__"] = str(source_path)
    old_cwd = Path.cwd()
    try:
        os.chdir(str(source_path.parent))
        exec(compile(python_code, str(source_path), "exec"), exec_globals)
        app = exec_globals.get("app") or exec_globals.get("application")
        create_app = exec_globals.get("create_app")
        if app is None and callable(create_app):
            app = create_app()
        if app is None and callable(exec_globals.get("main")):
            candidate = exec_globals["main"]()
            if isinstance(candidate, WebApp):
                app = candidate
        if app is None or not hasattr(app, "handle"):
            raise RuntimeError("No WebApp found. Define app/application, create_app(), or return a WebApp from main().")
        return app
    finally:
        os.chdir(str(old_cwd))


def _headers_from_environ(environ: Mapping[str, str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in environ.items():
        if key.startswith("HTTP_"):
            headers[key[5:].replace("_", "-").lower()] = value
    if environ.get("CONTENT_TYPE"):
        headers["content-type"] = environ["CONTENT_TYPE"]
    if environ.get("CONTENT_LENGTH"):
        headers["content-length"] = environ["CONTENT_LENGTH"]
    return headers


def request_from_cgi(environ: Mapping[str, str] | None = None, body: bytes | None = None) -> Request:
    env = dict(environ or os.environ)
    method = env.get("REQUEST_METHOD", "GET").upper()
    query = env.get("QUERY_STRING", "")
    path = env.get("PATH_INFO") or ""
    if not path or path == "/":
        uri = env.get("REQUEST_URI") or env.get("UNENCODED_URL") or "/"
        parsed = urlparse(uri)
        path = parsed.path or "/"
        if not query:
            query = parsed.query
    script_name = env.get("SCRIPT_NAME") or ""
    if path.startswith(script_name) and script_name not in {"", "/"}:
        path = path[len(script_name):] or "/"
    if not path.startswith("/"):
        path = "/" + path
    if body is None:
        length_raw = env.get("CONTENT_LENGTH") or "0"
        length = int(length_raw) if str(length_raw).isdigit() else 0
        body = sys.stdin.buffer.read(length) if length else b""
    remote_port_raw = env.get("REMOTE_PORT") or "0"
    remote_port = int(remote_port_raw) if str(remote_port_raw).isdigit() else 0
    return Request(method=method, path=path, query_string=query, headers=_headers_from_environ(env), body=body, client=(env.get("REMOTE_ADDR", ""), remote_port))


def handle_cgi_request(source_file: str | Path | None = None, environ: Mapping[str, str] | None = None, body: bytes | None = None) -> Response:
    return load_agilang_web_app(source_file).handle(request_from_cgi(environ, body))


def _emit_cgi_response(response: Response, stdout: Any = None) -> None:
    out = stdout or sys.stdout.buffer
    payload = response.to_bytes()
    reason = HTTPStatus(response.status).phrase if response.status in HTTPStatus._value2member_map_ else "OK"
    headers = {"Status": f"{response.status} {reason}", "Content-Type": response.headers.get("Content-Type", response.content_type), "Content-Length": str(len(payload))}
    for key, value in response.headers.items():
        if key.lower() not in {"content-type", "content-length", "status"}:
            headers[key] = str(value)
    raw = "".join(f"{k}: {v}\r\n" for k, v in headers.items()) + "\r\n"
    out.write(raw.encode("latin1"))
    if payload:
        out.write(payload)


def run_cgi(source_file: str | Path | None = None) -> None:
    try:
        response = handle_cgi_request(source_file)
    except Exception as exc:
        response = text_response(f"AGILANG CGI error: {type(exc).__name__}: {exc}", status=500)
    _emit_cgi_response(response)


def fastcgi_wsgi_app(source_file: str | Path | None = None):
    return wsgi_adapter(load_agilang_web_app(source_file))


def _flup_importable() -> bool:
    try:
        import flup.server.fcgi  # type: ignore  # noqa: F401
        return True
    except Exception:
        return False


def run_fastcgi(source_file: str | Path | None = None) -> None:
    try:
        from flup.server.fcgi import WSGIServer  # type: ignore
    except Exception:
        if os.environ.get("GATEWAY_INTERFACE"):
            run_cgi(source_file)
            return
        raise RuntimeError("FastCGI requires optional flup or host-provided FastCGI support. Use app.cgi for universal CGI.")
    WSGIServer(fastcgi_wsgi_app(source_file)).run()


def discover_shared_hosting(environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    env = dict(environ or os.environ)
    joined = " ".join(str(env.get(k, "")) for k in ("SERVER_SOFTWARE", "DOCUMENT_ROOT", "HOME", "PATH"))
    lower = joined.lower()
    panel = "unknown"
    if "cpanel" in lower or "/public_html" in lower:
        panel = "cpanel-like"
    if "plesk" in lower or "httpdocs" in lower:
        panel = "plesk-like"
    return {"panel": panel, "server_software": env.get("SERVER_SOFTWARE"), "document_root": env.get("DOCUMENT_ROOT"), "home": env.get("HOME"), "python": sys.executable, "python_version": platform.python_version(), "classic_cgi": True, "fastcgi_optional_dependency": "flup", "fastcgi_importable": _flup_importable(), "recommended_entry": "public_html/app.cgi" if panel != "unknown" else "public_html/app.cgi or passenger_wsgi.py"}


def shared_hosting_capabilities() -> dict[str, Any]:
    return {"classic_cgi": True, "fastcgi": _flup_importable(), "fastcgi_mode": "enabled" if _flup_importable() else "optional: install flup or use host-provided FastCGI", "wsgi_passenger": True, "cpanel_public_html_scaffold": True, "plesk_httpdocs_scaffold": True, "websocket_note": "Classic CGI/FastCGI is request/response. Run WebSockets through the AGILANG realtime server or native runtime behind a reverse proxy when the host allows long-running processes."}


def _write(path: Path, content: str, mode: int | None, files: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
    if mode is not None:
        path.chmod(mode)
    files.append(path)


def write_shared_hosting_files(root: str | Path | None = None, *, entry: str = "src/main.agi", target: str = "public_html", mode: str = "auto", force: bool = True) -> HostingScaffoldResult:
    project_root = Path(root or Path.cwd()).expanduser().resolve()
    target_dir = project_root / target
    files: list[Path] = []
    mode = (mode or "auto").lower()
    if mode not in {"auto", "cgi", "fastcgi", "passenger"}:
        raise ValueError("mode must be one of: auto, cgi, fastcgi, passenger")
    if target_dir.exists() and any(target_dir.iterdir()) and not force:
        raise FileExistsError(f"Target directory exists and is not empty: {target_dir}")
    handler = "app.fcgi" if mode == "fastcgi" else "app.cgi"
    htaccess_handler = "app.fcgi" if mode == "fastcgi" else "app.cgi"
    _write(target_dir / ".htaccess", f'''
        # AGILANG shared-hosting router for cPanel/Plesk Apache.
        Options +ExecCGI -Indexes
        AddHandler cgi-script .cgi
        AddHandler fcgid-script .fcgi
        DirectoryIndex {handler}

        RewriteEngine On
        RewriteCond %{{REQUEST_FILENAME}} !-f
        RewriteCond %{{REQUEST_FILENAME}} !-d
        RewriteRule ^(.*)$ {htaccess_handler}/$1 [QSA,L]
        ''', None, files)
    _write(target_dir / "app.cgi", f'''
        #!/usr/bin/env python3
        import os, sys
        from pathlib import Path
        PROJECT_ROOT = Path(__file__).resolve().parents[1]
        VENDOR_DIR = PROJECT_ROOT / "vendor"
        sys.path.insert(0, str(PROJECT_ROOT))
        sys.path.insert(0, str(VENDOR_DIR))
        os.environ.setdefault("AGILANG_PROJECT_ROOT", str(PROJECT_ROOT))
        os.environ.setdefault("AGILANG_APP_ENTRY", "{entry}")
        from agilang.cgi_runtime import run_cgi
        run_cgi(os.environ["AGILANG_APP_ENTRY"])
        ''', 0o755, files)
    _write(target_dir / "app.fcgi", f'''
        #!/usr/bin/env python3
        import os, sys
        from pathlib import Path
        PROJECT_ROOT = Path(__file__).resolve().parents[1]
        VENDOR_DIR = PROJECT_ROOT / "vendor"
        sys.path.insert(0, str(PROJECT_ROOT))
        sys.path.insert(0, str(VENDOR_DIR))
        os.environ.setdefault("AGILANG_PROJECT_ROOT", str(PROJECT_ROOT))
        os.environ.setdefault("AGILANG_APP_ENTRY", "{entry}")
        from agilang.cgi_runtime import run_fastcgi
        run_fastcgi(os.environ["AGILANG_APP_ENTRY"])
        ''', 0o755, files)
    _write(project_root / "passenger_wsgi.py", f'''
        # AGILANG WSGI entrypoint for cPanel Setup Python App / Plesk Python app.
        import os, sys
        from pathlib import Path
        PROJECT_ROOT = Path(__file__).resolve().parent
        VENDOR_DIR = PROJECT_ROOT / "vendor"
        sys.path.insert(0, str(PROJECT_ROOT))
        sys.path.insert(0, str(VENDOR_DIR))
        os.environ.setdefault("AGILANG_PROJECT_ROOT", str(PROJECT_ROOT))
        os.environ.setdefault("AGILANG_APP_ENTRY", "{entry}")
        from agilang.cgi_runtime import fastcgi_wsgi_app
        application = fastcgi_wsgi_app(os.environ["AGILANG_APP_ENTRY"])
        ''', None, files)
    _write(project_root / "deployment/CPANEL_PLESK_CGI_FASTCGI.md", f'''
        # cPanel / Plesk deployment for AGILANG

        This project includes classic CGI, optional FastCGI, and WSGI/Passenger entrypoints.

        ## Quick shared-hosting upload

        1. Upload the project folder to your hosting account.
        2. The generated `vendor/agilang/` runtime is bundled with the app, so ordinary shared hosting can run it without global installation.
        3. Point your document root to `public_html/` on cPanel or copy `public_html/*` into `httpdocs/` on Plesk.
        4. Make sure `app.cgi` and `app.fcgi` are executable: `chmod 755 public_html/app.cgi public_html/app.fcgi`.
        5. Open the domain.

        ## Generated entrypoints

        - `public_html/app.cgi` - universal CGI, most compatible.
        - `public_html/app.fcgi` - FastCGI when the host supports `flup`/`mod_fcgid`.
        - `passenger_wsgi.py` - cPanel Setup Python App / Plesk Python WSGI entry.
        - `public_html/.htaccess` - Apache rewrite rules, similar to PHP front-controller routing.

        ## Commands

        ```bash
        agi hosting doctor
        agi hosting capabilities
        agi hosting scaffold --mode auto --entry {entry}
        ```

        ## Important WebSocket note

        CGI/FastCGI request handlers are not designed for persistent WebSocket connections. Use `agi run src/realtime.agi` or AGILANG's native/hybrid runtime where the host allows long-running processes.
        ''', None, files)
    return HostingScaffoldResult(root=project_root, target=target_dir, files=files, mode=mode)


__all__ = ["HostingScaffoldResult", "discover_shared_hosting", "fastcgi_wsgi_app", "handle_cgi_request", "load_agilang_web_app", "request_from_cgi", "resolve_entry", "run_cgi", "run_fastcgi", "shared_hosting_capabilities", "write_shared_hosting_files"]
