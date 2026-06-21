"""Minimal AGILANG Language Server Protocol implementation.

This server supports initialize, didOpen/didChange diagnostics, completion,
hover, and shutdown over stdio JSON-RPC. It is dependency-free so it works in
VS Code, Neovim, or any editor that can start a stdio language server.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from . import __version__
from .checker import check_source
from .lexer import KEYWORDS

COMPLETIONS = sorted(
    set(KEYWORDS)
    | {
        "fn", "let", "const", "struct", "enum", "type", "pub", "return",
        "print", "assert_eq", "read_csv", "write_csv", "read_text", "write_text",
        "i32", "i64", "f64", "str", "bool", "void", "any",
    }
)


def _read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in {b"\r\n", b"\n"}:
            break
        key, value = line.decode("ascii").split(":", 1)
        headers[key.lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = sys.stdin.buffer.read(length)
    return json.loads(body.decode("utf-8"))


def _send(payload: dict[str, Any]) -> None:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()


def _response(req_id: Any, result: Any = None, error: Any = None) -> None:
    payload = {"jsonrpc": "2.0", "id": req_id}
    if error is not None:
        payload["error"] = error
    else:
        payload["result"] = result
    _send(payload)


def _notify(method: str, params: Any) -> None:
    _send({"jsonrpc": "2.0", "method": method, "params": params})


def _uri_to_path(uri: str) -> Path | None:
    if uri.startswith("file://"):
        return Path(uri[7:])
    return None


def _diagnostics_for(uri: str, text: str) -> list[dict[str, Any]]:
    path = _uri_to_path(uri)
    report = check_source(text, path)
    diagnostics = []
    for d in report.diagnostics:
        loc = d.location
        line = max(0, (loc.line - 1) if loc else 0)
        col = max(0, (loc.column - 1) if loc else 0)
        diagnostics.append(
            {
                "range": {"start": {"line": line, "character": col}, "end": {"line": line, "character": col + 1}},
                "severity": 1 if d.severity == "error" else 2,
                "code": d.code,
                "source": "agilang",
                "message": d.message + (("\n" + d.hint) if d.hint else ""),
            }
        )
    return diagnostics


def run_stdio_server() -> None:
    documents: dict[str, str] = {}
    shutdown = False
    while True:
        msg = _read_message()
        if msg is None:
            return
        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params") or {}

        if method == "initialize":
            _response(
                req_id,
                {
                    "serverInfo": {"name": "agilang-lsp", "version": __version__},
                    "capabilities": {
                        "textDocumentSync": 1,
                        "completionProvider": {"triggerCharacters": [".", ":"]},
                        "hoverProvider": True,
                    },
                },
            )
        elif method == "initialized":
            pass
        elif method == "shutdown":
            shutdown = True
            _response(req_id, None)
        elif method == "exit":
            return
        elif method == "textDocument/didOpen":
            doc = params.get("textDocument", {})
            uri = doc.get("uri", "")
            text = doc.get("text", "")
            documents[uri] = text
            _notify("textDocument/publishDiagnostics", {"uri": uri, "diagnostics": _diagnostics_for(uri, text)})
        elif method == "textDocument/didChange":
            uri = params.get("textDocument", {}).get("uri", "")
            changes = params.get("contentChanges", [])
            if changes:
                documents[uri] = changes[-1].get("text", documents.get(uri, ""))
            _notify("textDocument/publishDiagnostics", {"uri": uri, "diagnostics": _diagnostics_for(uri, documents.get(uri, ""))})
        elif method == "textDocument/completion":
            _response(req_id, {"isIncomplete": False, "items": [{"label": item, "kind": 14} for item in COMPLETIONS]})
        elif method == "textDocument/hover":
            _response(req_id, {"contents": {"kind": "markdown", "value": "**AGILANG v0.6**\n\nStatic diagnostics, completions, and compiler-aware tooling are active."}})
        elif req_id is not None:
            _response(req_id, error={"code": -32601, "message": f"Method not supported: {method}"})
