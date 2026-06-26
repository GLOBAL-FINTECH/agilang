"""
AGILANG Standard Library
=======================

This module contains a handful of utility functions intended to
simplify common tasks when writing AGILANG programs.  Because
AGILANG v0.3 ultimately transpiles down to Python, you can call
any Python code you like from within AGILANG functions; however,
the helpers in this module offer a friendlier interface for a few
frequently used operations:

* Data input/output: ``read_csv``, ``write_csv``, ``read_text``,
  ``write_text``.
* Web requests: ``http_get`` for simple HTTP GET requests.
* Simple statistics: ``mean``, ``median``, ``stddev`` on numeric lists.
* Machine learning: ``train_linear_regression`` and ``predict`` to
  perform basic regression using scikit‑learn.
* Plotting: ``plot`` uses matplotlib to create a quick line chart.

These functions are defined here so they are available as globals
when running AGILANG code.  You can easily extend this module to
wrap additional Python libraries such as pandas or NumPy.

NOTE: Some functions depend on third‑party packages.  If such a
package is not installed, a descriptive ImportError will be raised.
"""

from __future__ import annotations

import csv
import statistics
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

__all__ = [
    "read_csv", "write_csv", "read_text", "write_text",
    "http_get", "mean", "median", "stddev",
    "train_linear_regression", "train_logistic_regression", "train_decision_tree_classifier", "predict", "accuracy_score", "plot",
    "json_loads", "json_dumps", "random_int",
    "load_std_globals",
]


def read_csv(path: str | Path, *, header: bool = True) -> List[Dict[str, Any]]:
    """Read a CSV file into a list of dictionaries.

    Args:
        path: The filesystem path to a CSV file.
        header: Whether the file contains a header row.  If true,
            dictionary keys are drawn from the first row; otherwise
            keys are numbered ``col0``, ``col1``, etc.

    Returns:
        A list of dictionaries, one per row.
    """
    p = Path(path)
    with p.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return []
    keys: List[str]
    start_idx = 0
    if header:
        keys = [str(k) for k in rows[0]]
        start_idx = 1
    else:
        keys = [f"col{i}" for i in range(len(rows[0]))]
    result = []
    for r in rows[start_idx:]:
        row_dict: Dict[str, Any] = {}
        for k, v in zip(keys, r):
            # Try to cast numeric values
            try:
                if v.strip() == "":
                    row_dict[k] = None
                elif "." in v:
                    row_dict[k] = float(v)
                else:
                    row_dict[k] = int(v)
            except ValueError:
                row_dict[k] = v
        result.append(row_dict)
    return result


def write_csv(path: str | Path, rows: Sequence[Dict[str, Any]], *, header: bool = True) -> None:
    """Write a list of dictionaries to a CSV file.

    Args:
        path: Destination CSV path.
        rows: Iterable of dictionaries.  Keys must be the same for
            all rows; if not, missing keys will be filled with blank
            values.
        header: Whether to write a header row with column names.
    """
    p = Path(path)
    if not rows:
        p.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if header:
            writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def read_text(path: str | Path) -> str:
    """Read the entire contents of a text file."""
    return Path(path).read_text(encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    """Write text to a file, overwriting if it exists."""
    Path(path).write_text(text, encoding="utf-8")


def http_get(url: str) -> str:
    """Fetch the content of a URL as a string.

    Requires the ``requests`` library.  If it is not available, an
    ImportError will be raised.
    """
    try:
        import requests  # type: ignore
    except ImportError as e:
        raise ImportError(
            "The `requests` package is required for http_get()."
        ) from e
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def mean(values: Sequence[float]) -> float:
    """Return the arithmetic mean of a sequence of numbers."""
    return statistics.mean(values)


def median(values: Sequence[float]) -> float:
    """Return the median of a sequence of numbers."""
    return statistics.median(values)


def stddev(values: Sequence[float]) -> float:
    """Return the sample standard deviation of a sequence of numbers."""
    return statistics.stdev(values)


def train_linear_regression(data: Sequence[Sequence[float]], targets: Sequence[float]):
    """Train a simple linear regression model using scikit‑learn.

    Args:
        data: A sequence of feature vectors (rows).  Each inner
            sequence must have the same length.
        targets: A sequence of numeric target values.

    Returns:
        A trained scikit‑learn LinearRegression model.
    """
    try:
        from sklearn.linear_model import LinearRegression
    except ImportError as e:
        raise ImportError(
            "The `scikit-learn` package is required for train_linear_regression()."
        ) from e
    import numpy as np
    X = np.array(data, dtype=float)
    y = np.array(targets, dtype=float)
    model = LinearRegression()
    model.fit(X, y)
    return model


def train_logistic_regression(
    data: Sequence[Sequence[float]], targets: Sequence[int], *, max_iter: int = 100
) -> Any:
    """Train a logistic regression classifier using scikit‑learn.

    Args:
        data: A sequence of feature vectors.
        targets: A sequence of integer class labels (0/1 or more classes).
        max_iter: Maximum number of iterations for the solver.

    Returns:
        A trained scikit‑learn LogisticRegression model.
    """
    try:
        from sklearn.linear_model import LogisticRegression
    except ImportError as e:
        raise ImportError(
            "The `scikit-learn` package is required for train_logistic_regression()."
        ) from e
    import numpy as np
    X = np.array(data, dtype=float)
    y = np.array(targets, dtype=int)
    model = LogisticRegression(max_iter=max_iter)
    model.fit(X, y)
    return model


def train_decision_tree_classifier(
    data: Sequence[Sequence[float]], targets: Sequence[int], *, max_depth: int | None = None
) -> Any:
    """Train a decision tree classifier using scikit‑learn.

    Args:
        data: A sequence of feature vectors.
        targets: A sequence of integer class labels.
        max_depth: Optional maximum tree depth to control complexity.

    Returns:
        A trained scikit‑learn DecisionTreeClassifier model.
    """
    try:
        from sklearn.tree import DecisionTreeClassifier
    except ImportError as e:
        raise ImportError(
            "The `scikit-learn` package is required for train_decision_tree_classifier()."
        ) from e
    import numpy as np
    X = np.array(data, dtype=float)
    y = np.array(targets, dtype=int)
    model = DecisionTreeClassifier(max_depth=max_depth)
    model.fit(X, y)
    return model


def accuracy_score(model: Any, data: Sequence[Sequence[float]], targets: Sequence[int]) -> float:
    """Compute the classification accuracy of a model on a dataset.

    Args:
        model: A classifier that implements a predict() method.
        data: Sequence of feature vectors.
        targets: True class labels.

    Returns:
        The fraction of correct predictions (between 0 and 1).
    """
    import numpy as np
    X = np.array(data, dtype=float)
    true = np.array(targets, dtype=int)
    pred = model.predict(X)
    return float((pred == true).mean())


def json_loads(s: str) -> Any:
    """Deserialize a JSON string into Python objects.

    This is a thin wrapper around ``json.loads``.
    """
    import json
    return json.loads(s)


def json_dumps(obj: Any, *, indent: int | None = 2) -> str:
    """Serialize a Python object to a JSON string.

    Args:
        obj: The object to serialize.  Must be JSON serialisable.
        indent: Number of spaces to indent nested structures.  Set
            to ``None`` for a compact representation.

    Returns:
        A JSON string.
    """
    import json
    return json.dumps(obj, indent=indent)


def random_int(a: int, b: int) -> int:
    """Return a random integer N such that ``a <= N <= b``.

    Thin wrapper around ``random.randint``.
    """
    import random
    return random.randint(a, b)


def predict(model: Any, data: Sequence[Sequence[float]]) -> List[float]:
    """Generate predictions from a previously trained model.

    Args:
        model: A model object returned by ``train_linear_regression``.
        data: A sequence of feature vectors.

    Returns:
        A list of predicted values.
    """
    import numpy as np
    X = np.array(data, dtype=float)
    preds = model.predict(X)
    return preds.tolist()


def plot(x: Sequence[float], y: Sequence[float], *, title: str | None = None) -> None:
    """Plot a simple line chart using matplotlib.

    Args:
        x: Sequence of x coordinates.
        y: Sequence of y coordinates.
        title: Optional plot title.

    The plot will display in a popup window if running in an
    environment that supports it.  In headless environments the call
    will succeed but nothing will be shown.
    """
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except ImportError as e:
        raise ImportError(
            "The `matplotlib` package is required for plotting."
        ) from e
    plt.figure()
    plt.plot(list(x), list(y))
    if title:
        plt.title(title)
    plt.xlabel("x")
    plt.ylabel("y")
    plt.grid(True)
    plt.show()


def load_std_globals() -> Dict[str, Any]:
    """Return a dictionary of standard functions to inject into the execution environment.

    The returned dictionary includes all names defined in this module
    (excluding private names starting with an underscore).  When
    evaluating AGILANG code, these functions will be available as
    globals.
    """
    std_globals: Dict[str, Any] = {}
    for name, value in globals().items():
        if name.startswith("_"):
            continue
        if name in ("load_std_globals", "__all__", "statistics"):
            continue
        std_globals[name] = value
    return std_globals
# --- v0.5 production runtime additions ---

def read_json(path: str | Path) -> Any:
    """Read JSON from a file."""
    import json
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, obj: Any, *, indent: int | None = 2) -> None:
    """Write JSON to a file."""
    import json
    Path(path).write_text(json.dumps(obj, indent=indent), encoding="utf-8")


def ensure_dir(path: str | Path) -> str:
    """Create a directory if it does not exist and return its path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def now_iso() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def assert_eq(actual: Any, expected: Any, message: str | None = None) -> None:
    """Raise AssertionError unless actual == expected."""
    if actual != expected:
        raise AssertionError(message or f"assert_eq failed: {actual!r} != {expected!r}")

# --- v0.7 realtime transport runtime wrappers ---

def websocket_listen(host: str = "127.0.0.1", port: int = 0, path: str = "/") -> Any:
    """Create an AGILANG WebSocket server."""
    from agilang.realtime import websocket_listen as _websocket_listen
    return _websocket_listen(host, port, path)


def websocket_connect(url: str, timeout: float = 5.0) -> Any:
    """Connect to a WebSocket server as an AGILANG client."""
    from agilang.realtime import websocket_connect as _websocket_connect
    return _websocket_connect(url, timeout)


def realtime_channel(name: str) -> Any:
    """Create a named in-process realtime channel."""
    from agilang.realtime import realtime_channel as _realtime_channel
    return _realtime_channel(name)


def pubsub_bus() -> Any:
    """Create an in-process AGILANG pub/sub message bus."""
    from agilang.realtime import pubsub_bus as _pubsub_bus
    return _pubsub_bus()


def json_event(event_type: str, payload: Any = None, topic: str | None = None) -> str:
    """Create a compact realtime JSON event envelope."""
    from agilang.realtime import json_event as _json_event
    return _json_event(event_type, payload, topic)


def parse_json_event(raw: str | bytes) -> Dict[str, Any]:
    """Parse a realtime JSON event envelope into a dictionary."""
    from agilang.realtime import parse_json_event as _parse_json_event
    return _parse_json_event(raw)

# --- v0.8 web framework runtime wrappers ---

def web_app(name: str = "agilang", debug: bool = False) -> Any:
    """Create an AGILANG HTTP web application."""
    from agilang.web import web_app as _web_app
    return _web_app(name=name, debug=debug)


def text_response(text: str, status: int = 200, headers: Dict[str, str] | None = None) -> Any:
    """Return a plain-text HTTP response."""
    from agilang.web import text_response as _text_response
    return _text_response(text, status=status, headers=headers)


def html_response(html_text: str, status: int = 200, headers: Dict[str, str] | None = None) -> Any:
    """Return an HTML HTTP response."""
    from agilang.web import html_response as _html_response
    return _html_response(html_text, status=status, headers=headers)


def json_response(data: Any, status: int = 200, headers: Dict[str, str] | None = None) -> Any:
    """Return a JSON HTTP response."""
    from agilang.web import json_response as _json_response
    return _json_response(data, status=status, headers=headers)


def redirect(location: str, status: int = 302) -> Any:
    """Return an HTTP redirect response."""
    from agilang.web import redirect as _redirect
    return _redirect(location, status=status)


def file_response(path: str | Path, download_name: str | None = None) -> Any:
    """Return a file download/static response."""
    from agilang.web import file_response as _file_response
    return _file_response(path, download_name=download_name)


def render_template(template: str | Path, context: Dict[str, Any] | None = None, **kwargs: Any) -> str:
    """Render a tiny {{ name }} HTML template."""
    from agilang.web import render_template as _render_template
    return _render_template(template, context, **kwargs)


def seo_tags(meta: Dict[str, Any] | None = None, **kwargs: Any) -> str:
    """Render SEO, Open Graph, Twitter, canonical, and robots tags."""
    from agilang.web import seo_tags as _seo_tags
    return _seo_tags(meta, **kwargs)


def render_ags(template: str | Path, context: Dict[str, Any] | None = None, **kwargs: Any) -> Dict[str, Any]:
    """Render an AGILANG .ags single-file view into body + metadata."""
    from agilang.web import render_ags as _render_ags
    return _render_ags(template, context, **kwargs)


def web_get(url: str, timeout: float = 5.0, headers: Dict[str, str] | None = None) -> str:
    """HTTP GET helper used by AGILANG examples/tests."""
    from agilang.web import web_get as _web_get
    return _web_get(url, timeout=timeout, headers=headers)


def web_post_json(url: str, payload: Any, timeout: float = 5.0, headers: Dict[str, str] | None = None) -> str:
    """HTTP POST JSON helper used by AGILANG examples/tests."""
    from agilang.web import web_post_json as _web_post_json
    return _web_post_json(url, payload, timeout=timeout, headers=headers)


def hash_password(password: str, iterations: int = 260000) -> str:
    """Hash a password with PBKDF2-SHA256."""
    from agilang.web import hash_password as _hash_password
    return _hash_password(password, iterations=iterations)


def verify_password(password: str, encoded: str) -> bool:
    """Verify a password against a PBKDF2-SHA256 hash."""
    from agilang.web import verify_password as _verify_password
    return _verify_password(password, encoded)


def sign_cookie(data: Dict[str, Any], secret: str, max_age: int | None = None) -> str:
    """Create a signed cookie token."""
    from agilang.web import sign_cookie as _sign_cookie
    return _sign_cookie(data, secret, max_age=max_age)


def verify_cookie(token: str, secret: str) -> Dict[str, Any] | None:
    """Verify and decode a signed cookie token."""
    from agilang.web import verify_cookie as _verify_cookie
    return _verify_cookie(token, secret)


def sqlite_db(path: str | Path) -> Any:
    """Create a small SQLite helper for AGILANG web apps."""
    from agilang.web import sqlite_db as _sqlite_db
    return _sqlite_db(path)


def mysql_db(*, host: str = "127.0.0.1", port: int = 3306, user: str = "root", password: str = "", database: str = "", charset: str = "utf8mb4") -> Any:
    """Create a small MySQL helper for AGILANG web apps."""
    from agilang.web import mysql_db as _mysql_db
    return _mysql_db(host=host, port=port, user=user, password=password, database=database, charset=charset)

# --- v0.9 full web platform wrappers ---

def string(default: str | None = None, nullable: bool = True, unique: bool = False) -> Any:
    from agilang.web import string as _string
    return _string(default=default, nullable=nullable, unique=unique)


def integer(default: int | None = None, primary_key: bool = False, nullable: bool = True, unique: bool = False) -> Any:
    from agilang.web import integer as _integer
    return _integer(default=default, primary_key=primary_key, nullable=nullable, unique=unique)


def real(default: float | None = None, nullable: bool = True) -> Any:
    from agilang.web import real as _real
    return _real(default=default, nullable=nullable)


def boolean(default: bool | None = None, nullable: bool = True) -> Any:
    from agilang.web import boolean as _boolean
    return _boolean(default=default, nullable=nullable)


def model(name: str, fields: Dict[str, Any], table: str | None = None) -> Any:
    from agilang.web import model as _model
    return _model(name, fields, table=table)


def migrate(db: Any, migrations: Sequence[Any]) -> List[str]:
    from agilang.web import migrate as _migrate
    return _migrate(db, migrations)


def validate(data: Dict[str, Any], schema: Dict[str, Any]) -> Any:
    from agilang.web import validate as _validate
    return _validate(data, schema)


def validation_middleware(schema: Dict[str, Any]) -> Any:
    from agilang.web import validation_middleware as _validation_middleware
    return _validation_middleware(schema)


def csrf_token(secret: str, session_id: str | None = None) -> str:
    from agilang.web import csrf_token as _csrf_token
    return _csrf_token(secret, session_id=session_id)


def csrf_input(token: str) -> str:
    from agilang.web import csrf_input as _csrf_input
    return _csrf_input(token)


def csrf_protect(secret: str) -> Any:
    from agilang.web import csrf_protect as _csrf_protect
    return _csrf_protect(secret)


def login_user(response: Any, user: Dict[str, Any], secret: str, cookie_name: str = "agi_session", max_age: int = 86400) -> Any:
    from agilang.web import login_user as _login_user
    return _login_user(response, user, secret, cookie_name=cookie_name, max_age=max_age)


def current_user(request: Any, secret: str, cookie_name: str = "agi_session") -> Dict[str, Any] | None:
    from agilang.web import current_user as _current_user
    return _current_user(request, secret, cookie_name=cookie_name)


def logout_user(response: Any, cookie_name: str = "agi_session") -> Any:
    from agilang.web import logout_user as _logout_user
    return _logout_user(response, cookie_name=cookie_name)


def auth_required(secret: str, cookie_name: str = "agi_session", redirect_to: str | None = None) -> Any:
    from agilang.web import auth_required as _auth_required
    return _auth_required(secret, cookie_name=cookie_name, redirect_to=redirect_to)


def job_queue(workers: int = 1) -> Any:
    from agilang.web import job_queue as _job_queue
    return _job_queue(workers=workers)


def wsgi_adapter(app: Any) -> Any:
    from agilang.web import wsgi_adapter as _wsgi_adapter
    return _wsgi_adapter(app)


def asgi_adapter(app: Any) -> Any:
    from agilang.web import asgi_adapter as _asgi_adapter
    return _asgi_adapter(app)

# --- v1.0 WebRTC, security, and React/mobile platform wrappers ---

def webrtc_peer(peer_id: str | None = None, metadata: Dict[str, Any] | None = None) -> Any:
    from agilang.webrtc import webrtc_peer as _webrtc_peer
    return _webrtc_peer(peer_id=peer_id, metadata=metadata)


def webrtc_room(name: str) -> Any:
    from agilang.webrtc import webrtc_room as _webrtc_room
    return _webrtc_room(name)


def webrtc_signal(signal_type: str, from_peer: str, payload: Dict[str, Any] | None = None, to_peer: str | None = None, room: str | None = None) -> str:
    from agilang.webrtc import webrtc_signal as _webrtc_signal
    return _webrtc_signal(signal_type, from_peer, payload, to_peer=to_peer, room=room)


def webrtc_offer(sdp: str, from_peer: str, to_peer: str | None = None, room: str | None = None) -> str:
    from agilang.webrtc import webrtc_offer as _webrtc_offer
    return _webrtc_offer(sdp, from_peer, to_peer=to_peer, room=room)


def webrtc_answer(sdp: str, from_peer: str, to_peer: str | None = None, room: str | None = None) -> str:
    from agilang.webrtc import webrtc_answer as _webrtc_answer
    return _webrtc_answer(sdp, from_peer, to_peer=to_peer, room=room)


def webrtc_ice(candidate: Dict[str, Any], from_peer: str, to_peer: str | None = None, room: str | None = None) -> str:
    from agilang.webrtc import webrtc_ice as _webrtc_ice
    return _webrtc_ice(candidate, from_peer, to_peer=to_peer, room=room)


def parse_webrtc_signal(raw: str | bytes) -> Dict[str, Any]:
    from agilang.webrtc import parse_webrtc_signal as _parse_webrtc_signal
    return _parse_webrtc_signal(raw)


def webrtc_signal_server(host: str = "127.0.0.1", port: int = 0, path: str = "/webrtc", auth_token: str | None = None) -> Any:
    from agilang.webrtc import webrtc_signal_server as _webrtc_signal_server
    return _webrtc_signal_server(host, port, path, auth_token=auth_token)


def security_config(**kwargs: Any) -> Any:
    from agilang.security import security_config as _security_config
    return _security_config(**kwargs)


def security_headers(config: Any = None) -> Any:
    from agilang.security import security_headers as _security_headers
    return _security_headers(config)


def body_limit(max_bytes: int = 1024 * 1024) -> Any:
    from agilang.security import body_limit as _body_limit
    return _body_limit(max_bytes)


def rate_limit(limit: int = 120, window_seconds: int = 60) -> Any:
    from agilang.security import rate_limit as _rate_limit
    return _rate_limit(limit=limit, window_seconds=window_seconds)


def secure_random_token(bytes_len: int = 32) -> str:
    from agilang.security import secure_random_token as _secure_random_token
    return _secure_random_token(bytes_len)


def hmac_sign(message: str | bytes, secret: str | bytes) -> str:
    from agilang.security import hmac_sign as _hmac_sign
    return _hmac_sign(message, secret)


def hmac_verify(message: str | bytes, secret: str | bytes, signature: str) -> bool:
    from agilang.security import hmac_verify as _hmac_verify
    return _hmac_verify(message, secret, signature)


def api_key_hash(api_key: str) -> str:
    from agilang.security import api_key_hash as _api_key_hash
    return _api_key_hash(api_key)


def verify_api_key(api_key: str, encoded: str) -> bool:
    from agilang.security import verify_api_key as _verify_api_key
    return _verify_api_key(api_key, encoded)

# --- v1.1 native hybrid web runtime wrappers ---

def hybrid_web_runtime(mode: str = "hybrid", auto_build_native: bool = False) -> Any:
    """Create a C+Python hybrid AGILANG web runtime selector."""
    from agilang.hybrid_runtime import hybrid_web_runtime as _hybrid_web_runtime
    return _hybrid_web_runtime(mode, auto_build_native=auto_build_native)


def native_web_runtime(auto_build: bool = True) -> Any:
    """Load or build the AGILANG native C HTTP/WebSocket runtime."""
    from agilang.hybrid_runtime import native_web_runtime as _native_web_runtime
    return _native_web_runtime(auto_build=auto_build)


def native_runtime_status(build: bool = False) -> Dict[str, Any]:
    """Return diagnostics for the native C runtime."""
    from agilang.hybrid_runtime import native_runtime_status as _native_runtime_status
    return _native_runtime_status(build=build)


def native_runtime_available() -> bool:
    """Return True if the C runtime can be compiled, loaded, and self-tested."""
    from agilang.hybrid_runtime import native_runtime_available as _native_runtime_available
    return _native_runtime_available()


def agilab_web_runtime(mode: str = "hybrid", auto_build_native: bool = False) -> Any:
    """AGILAB-branded alias for AGILANG's hybrid web runtime."""
    from agilang.hybrid_runtime import agilab_web_runtime as _agilab_web_runtime
    return _agilab_web_runtime(mode, auto_build_native=auto_build_native)


def agilab_native_runtime(auto_build: bool = True) -> Any:
    """AGILAB-branded alias for the native C runtime loader."""
    from agilang.hybrid_runtime import agilab_native_runtime as _agilab_native_runtime
    return _agilab_native_runtime(auto_build=auto_build)

# --- v1.2 precompiled native runtime wrappers ---

def native_prebuilt_status() -> Dict[str, Any]:
    """Return bundled precompiled native runtime artifacts for this platform."""
    from agilang.hybrid_runtime import native_prebuilt_status as _native_prebuilt_status
    return _native_prebuilt_status()


def native_prebuilt_runtime_install(output_dir: str | None = None) -> Any:
    """Install the matching bundled precompiled native runtime, if available."""
    from agilang.hybrid_runtime import native_prebuilt_runtime_install as _native_prebuilt_runtime_install
    return _native_prebuilt_runtime_install(output_dir)

# --- v1.3 cross-platform runtime wrappers ---
def native_platform_matrix() -> Dict[str, Any]:
    from agilang.hybrid_runtime import native_platform_matrix as _native_platform_matrix
    return _native_platform_matrix()


# --- v1.4 CGI/FastCGI shared-hosting runtime wrappers ---

def shared_hosting_capabilities() -> Dict[str, Any]:
    """Return CGI/FastCGI/cPanel/Plesk shared-hosting capabilities."""
    from agilang.cgi_runtime import shared_hosting_capabilities as _caps
    return _caps()


def shared_hosting_detect() -> Dict[str, Any]:
    """Best-effort detection for cPanel/Plesk-style hosting environments."""
    from agilang.cgi_runtime import discover_shared_hosting as _detect
    return _detect()


def cgi_request() -> Any:
    """Create a Request object from the current CGI/FastCGI environment."""
    from agilang.cgi_runtime import request_from_cgi as _request
    return _request()


# --- v1.5 mobile native runtime bridge wrappers ---

def mobile_runtime_matrix() -> Dict[str, Any]:
    """Return Android/iOS native runtime bridge targets and artifact availability."""
    from agilang.mobile_runtime import mobile_runtime_matrix as _mobile_runtime_matrix
    return _mobile_runtime_matrix()


def mobile_runtime_capabilities() -> Dict[str, Any]:
    """Return AGILANG mobile web/native bridge capability flags."""
    from agilang.mobile_runtime import mobile_runtime_capabilities as _mobile_runtime_capabilities
    return _mobile_runtime_capabilities()


def mobile_runtime_doctor() -> Dict[str, Any]:
    """Return local mobile toolchain diagnostics."""
    from agilang.mobile_runtime import mobile_runtime_doctor as _mobile_runtime_doctor
    return _mobile_runtime_doctor()


# --- v1.6 general systems, low-level networking, EVM, and interop wrappers ---

def tcp_listen(host: str = "127.0.0.1", port: int = 0, handler: Any = None) -> Any:
    from agilang.lowlevel_network import tcp_listen as _tcp_listen
    return _tcp_listen(host, port, handler)


def tcp_connect(host: str, port: int, timeout: float = 5.0) -> Any:
    from agilang.lowlevel_network import tcp_connect as _tcp_connect
    return _tcp_connect(host, port, timeout)


def udp_socket(host: str = "127.0.0.1", port: int = 0, broadcast: bool = False) -> Any:
    from agilang.lowlevel_network import udp_socket as _udp_socket
    return _udp_socket(host, port, broadcast)


def packet_frame(payload: Any) -> bytes:
    from agilang.lowlevel_network import packet_frame as _packet_frame
    return _packet_frame(payload)


def packet_unframe(data: bytes) -> bytes:
    from agilang.lowlevel_network import packet_unframe as _packet_unframe
    return _packet_unframe(data)


def packet_json(event_type: str, payload: Any = None, topic: str | None = None) -> bytes:
    from agilang.lowlevel_network import packet_json as _packet_json
    return _packet_json(event_type, payload, topic)


def packet_json_parse(data: bytes) -> Dict[str, Any]:
    from agilang.lowlevel_network import packet_json_parse as _packet_json_parse
    return _packet_json_parse(data)


def gossip_node(host: str = "127.0.0.1", port: int = 0, node_id: str | None = None, seeds: Any = None) -> Any:
    from agilang.lowlevel_network import gossip_node as _gossip_node
    return _gossip_node(host, port, node_id=node_id, seeds=seeds)


def lowlevel_network_capabilities() -> Dict[str, Any]:
    from agilang.lowlevel_network import lowlevel_network_capabilities as _caps
    return _caps()


def evm_capabilities() -> Dict[str, Any]:
    from agilang.evm import evm_capabilities as _evm_capabilities
    return _evm_capabilities()


def evm_keccak(data: Any) -> str:
    from agilang.evm import evm_keccak as _evm_keccak
    return _evm_keccak(data)


def evm_function_selector(signature: str) -> str:
    from agilang.evm import evm_function_selector as _evm_function_selector
    return _evm_function_selector(signature)


def evm_abi_encode(types: Any, values: Any) -> str:
    from agilang.evm import evm_abi_encode as _evm_abi_encode
    return _evm_abi_encode(types, values)


def evm_contract_call_data(signature: str, types: Any = None, values: Any = None) -> str:
    from agilang.evm import evm_contract_call_data as _evm_contract_call_data
    return _evm_contract_call_data(signature, types, values)


def evm_bytecode_builder() -> Any:
    from agilang.evm import evm_bytecode_builder as _evm_bytecode_builder
    return _evm_bytecode_builder()


def evm_disassemble(bytecode: Any) -> Any:
    from agilang.evm import evm_disassemble as _evm_disassemble
    return _evm_disassemble(bytecode)


def evm_abi_decode(types: Any, data: Any) -> Any:
    from agilang.evm import evm_abi_decode as _evm_abi_decode
    return _evm_abi_decode(types, data)


def evm_execute(bytecode: Any, calldata: Any = b"", gas: int = 10000000, context: Any = None, trace: bool = False) -> Dict[str, Any]:
    from agilang.evm import evm_execute as _evm_execute
    return _evm_execute(bytecode, calldata, gas, context, trace)


def evm_simulate_call(code: Any, calldata: Any = b"", storage: Any = None, gas: int = 10000000, trace: bool = False) -> Dict[str, Any]:
    from agilang.evm import evm_simulate_call as _evm_simulate_call
    return _evm_simulate_call(code, calldata, storage=storage, gas=gas, trace=trace)


def evm_estimate_gas(bytecode: Any, calldata: Any = b"", gas_limit: int = 10000000) -> int:
    from agilang.evm import evm_estimate_gas as _evm_estimate_gas
    return _evm_estimate_gas(bytecode, calldata, gas_limit=gas_limit)


def evm_trace(bytecode: Any, calldata: Any = b"", gas: int = 10000000) -> Any:
    from agilang.evm import evm_trace as _evm_trace
    return _evm_trace(bytecode, calldata, gas)


def evm_world_state(accounts: Any = None) -> Any:
    from agilang.evm import evm_world_state as _evm_world_state
    return _evm_world_state(accounts)


def evm_interpreter(world: Any = None, trace: bool = False) -> Any:
    from agilang.evm import evm_interpreter as _evm_interpreter
    return _evm_interpreter(world, trace=trace)


def evm_rlp_encode(value: Any) -> str:
    from agilang.evm import evm_rlp_encode as _evm_rlp_encode
    return _evm_rlp_encode(value)


def evm_legacy_unsigned_tx(nonce: int, gas_price: int, gas_limit: int, to: str, value: int, data: Any = b"", chain_id: int | None = None) -> Dict[str, Any]:
    from agilang.evm import evm_legacy_unsigned_tx as _evm_legacy_unsigned_tx
    return _evm_legacy_unsigned_tx(nonce, gas_price, gas_limit, to, value, data, chain_id)


def evm_external_engine(name: str = "auto") -> Dict[str, Any]:
    from agilang.evm import evm_external_engine as _evm_external_engine
    return _evm_external_engine(name)


def evm_rpc(url: str, timeout: float = 10.0) -> Any:
    from agilang.evm import evm_rpc as _evm_rpc
    return _evm_rpc(url, timeout)


def python_package(name: str, required: bool = True) -> Any:
    from agilang.interop import python_package as _python_package
    return _python_package(name, required)


def python_package_status(names: Any) -> Dict[str, Any]:
    from agilang.interop import python_package_status as _python_package_status
    return _python_package_status(names)


def native_library(path: str) -> Any:
    from agilang.interop import native_library as _native_library
    return _native_library(path)


def capability_manifest(path: str) -> Dict[str, Any]:
    from agilang.interop import capability_manifest as _capability_manifest
    return _capability_manifest(path)


def interop_capabilities() -> Dict[str, Any]:
    from agilang.interop import interop_capabilities as _interop_capabilities
    return _interop_capabilities()


def systems_capabilities() -> Dict[str, Any]:
    from agilang.interop import systems_capabilities as _systems_capabilities
    return _systems_capabilities()


# --- v1.7 zero-knowledge systems wrappers ---

def zk_capabilities() -> Dict[str, Any]:
    from agilang.zk import zk_capabilities as _zk_capabilities
    return _zk_capabilities()


def zk_field(name: str = "bn254", modulus: int | None = None) -> Any:
    from agilang.zk import zk_field as _zk_field
    return _zk_field(name, modulus)


def zk_circuit(name: str = "circuit", field_name: str = "bn254") -> Any:
    from agilang.zk import zk_circuit as _zk_circuit
    return _zk_circuit(name, field_name)


def zk_commit(value: Any, salt: str | None = None) -> Dict[str, Any]:
    from agilang.zk import zk_commit as _zk_commit
    return _zk_commit(value, salt)


def zk_verify_commitment(commitment: Any, value: Any, salt: str | None = None) -> bool:
    from agilang.zk import zk_verify_commitment as _zk_verify_commitment
    return _zk_verify_commitment(commitment, value, salt)


def zk_merkle_tree(leaves: Any) -> Any:
    from agilang.zk import zk_merkle_tree as _zk_merkle_tree
    return _zk_merkle_tree(leaves)


def zk_merkle_proof(leaves: Any, index: int) -> Dict[str, Any]:
    from agilang.zk import zk_merkle_proof as _zk_merkle_proof
    return _zk_merkle_proof(leaves, index)


def zk_verify_merkle_proof(leaf: Any, index: int, proof: Any, root: str) -> bool:
    from agilang.zk import zk_verify_merkle_proof as _zk_verify_merkle_proof
    return _zk_verify_merkle_proof(leaf, index, proof, root)


def zk_nullifier(secret: Any, scope: str = "default") -> str:
    from agilang.zk import zk_nullifier as _zk_nullifier
    return _zk_nullifier(secret, scope)


def zk_schnorr_keypair(secret: int | None = None, generator: int = 5, modulus: int | None = None) -> Dict[str, int]:
    from agilang.zk import zk_schnorr_keypair as _zk_schnorr_keypair, DEV_SCHNORR_MODULUS
    return _zk_schnorr_keypair(secret, generator=generator, modulus=modulus or DEV_SCHNORR_MODULUS)


def zk_schnorr_prove(secret: int, message: Any = "", nonce: int | None = None, generator: int = 5, modulus: int | None = None) -> Dict[str, Any]:
    from agilang.zk import zk_schnorr_prove as _zk_schnorr_prove, DEV_SCHNORR_MODULUS
    return _zk_schnorr_prove(secret, message, nonce=nonce, generator=generator, modulus=modulus or DEV_SCHNORR_MODULUS)


def zk_schnorr_verify(proof: Dict[str, Any], message: Any = None) -> bool:
    from agilang.zk import zk_schnorr_verify as _zk_schnorr_verify
    return _zk_schnorr_verify(proof, message)


def zk_bridge_status() -> Dict[str, Any]:
    from agilang.zk import zk_bridge_status as _zk_bridge_status
    return _zk_bridge_status()


def zk_external_engine(name: str, command: str | None = None, workdir: str | Path | None = None) -> Any:
    from agilang.zk import zk_external_engine as _zk_external_engine
    return _zk_external_engine(name, command=command, workdir=workdir)


def zk_demo_payload() -> Dict[str, Any]:
    from agilang.zk import zk_demo_payload as _zk_demo_payload
    return _zk_demo_payload()

# --- v1.9 full blockchain framework wrappers ---

def blockchain_capabilities() -> Dict[str, Any]:
    """Show AGILANG full blockchain framework capabilities."""
    from agilang.blockchain import blockchain_capabilities as _blockchain_capabilities
    return _blockchain_capabilities()


def blockchain_config(*args: Any, **kwargs: Any) -> Any:
    """Create a configurable Proof-of-Stake blockchain configuration."""
    from agilang.blockchain import blockchain_config as _blockchain_config
    return _blockchain_config(*args, **kwargs)


def blockchain_transaction(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Create a deterministic AGILANG blockchain transaction dictionary."""
    from agilang.blockchain import blockchain_transaction as _blockchain_transaction
    return _blockchain_transaction(*args, **kwargs)


def blockchain_merkle_root(items: Any) -> str:
    """Compute a deterministic Merkle root over items."""
    from agilang.blockchain import blockchain_merkle_root as _blockchain_merkle_root
    return _blockchain_merkle_root(items)


def pos_consensus_engine(config: Any) -> Any:
    """Create a Proof-of-Stake consensus engine."""
    from agilang.blockchain import pos_consensus_engine as _pos_consensus_engine
    return _pos_consensus_engine(config)


def blockchain_node(config: Any = None, db_path: str | Path = ":memory:", node_id: str | None = None) -> Any:
    """Create a full AGILANG blockchain node with DB, mempool and PoS consensus."""
    from agilang.blockchain import blockchain_node as _blockchain_node
    return _blockchain_node(config, db_path=db_path, node_id=node_id)


def blockchain_devnet(config: Any = None, validators: Any = None) -> Any:
    """Create an in-process blockchain devnet with connected validator nodes."""
    from agilang.blockchain import blockchain_devnet as _blockchain_devnet
    return _blockchain_devnet(config, validators=validators)


def blockchain_demo() -> Dict[str, Any]:
    """Run a complete AGILANG blockchain demo and return status data."""
    from agilang.blockchain import blockchain_demo as _blockchain_demo
    return _blockchain_demo()


# AGILANG AI / ML / tensor helpers
def ai_runtime_info() -> Dict[str, Any]:
    from agilang.ml import ai_runtime_info as _f
    return _f()

def ml_read_csv(path: str, numeric: bool = True) -> Any:
    from agilang.ml import ml_read_csv as _f
    return _f(path, numeric=numeric)

def ml_write_csv(path: str, rows: Any) -> Dict[str, Any]:
    from agilang.ml import ml_write_csv as _f
    return _f(path, rows)

def ml_missing_values(rows: Any) -> Dict[str, int]:
    from agilang.ml import ml_missing_values as _f
    return _f(rows)

def ml_fill_missing(rows: Any, strategy: str = "mean", fill_value: Any = 0) -> Any:
    from agilang.ml import ml_fill_missing as _f
    return _f(rows, strategy=strategy, fill_value=fill_value)

def ml_standard_scale(rows: Any, columns: Any) -> Any:
    from agilang.ml import ml_standard_scale as _f
    return _f(rows, columns)

def ml_logistic_regression(rows: Any, target: str, features: Any, epochs: int = 1200, learning_rate: float = 0.1) -> Dict[str, Any]:
    from agilang.ml import ml_logistic_regression as _f
    return _f(rows, target, features, epochs=epochs, learning_rate=learning_rate)

def ml_predict_logistic(model: Dict[str, Any], row: Dict[str, Any], threshold: float = 0.5) -> Dict[str, Any]:
    from agilang.ml import ml_predict_logistic as _f
    return _f(model, row, threshold=threshold)

def ml_kmeans(rows: Any, features: Any, k: int = 2, iterations: int = 30) -> Dict[str, Any]:
    from agilang.ml import ml_kmeans as _f
    return _f(rows, features, k=k, iterations=iterations)

def ml_decision_stump(rows: Any, target: str, features: Any) -> Dict[str, Any]:
    from agilang.ml import ml_decision_stump as _f
    return _f(rows, target, features)

def ml_predict_tree(model: Dict[str, Any], row: Dict[str, Any]) -> Any:
    from agilang.ml import ml_predict_tree as _f
    return _f(model, row)

def ml_accuracy(y_true: Any, y_pred: Any) -> float:
    from agilang.ml import ml_accuracy as _f
    return _f(y_true, y_pred)

def ml_confusion_matrix(y_true: Any, y_pred: Any) -> Dict[str, Any]:
    from agilang.ml import ml_confusion_matrix as _f
    return _f(y_true, y_pred)

def ml_neural_network_train(rows: Any, target: str, features: Any, hidden: int = 4, epochs: int = 1000, learning_rate: float = 0.1, seed: int = 42) -> Dict[str, Any]:
    from agilang.ml import ml_neural_network_train as _f
    return _f(rows, target, features, hidden=hidden, epochs=epochs, learning_rate=learning_rate, seed=seed)

def ml_neural_network_predict(model: Dict[str, Any], row: Dict[str, Any], threshold: float = 0.5) -> Dict[str, Any]:
    from agilang.ml import ml_neural_network_predict as _f
    return _f(model, row, threshold=threshold)

def ml_chart_spec(rows: Any, chart: str, x: str, y: str | None = None, title: str = "AGILANG Chart") -> Dict[str, Any]:
    from agilang.ml import ml_chart_spec as _f
    return _f(rows, chart, x, y, title)

def ml_save_model(model: Dict[str, Any], path: str) -> Dict[str, Any]:
    from agilang.ml import ml_save_model as _f
    return _f(model, path)

def ml_load_model(path: str) -> Dict[str, Any]:
    from agilang.ml import ml_load_model as _f
    return _f(path)

def tensor_shape(value: Any) -> Any:
    from agilang.ml import tensor_shape as _f
    return _f(value)

def tensor_zeros(shape: Any) -> Any:
    from agilang.ml import tensor_zeros as _f
    return _f(shape)

def tensor_random(shape: Any, seed: int = 42, low: float = -0.1, high: float = 0.1) -> Any:
    from agilang.ml import tensor_random as _f
    return _f(shape, seed=seed, low=low, high=high)

def tensor_transpose(matrix: Any) -> Any:
    from agilang.ml import tensor_transpose as _f
    return _f(matrix)

def tensor_dot(a: Any, b: Any) -> float:
    from agilang.ml import tensor_dot as _f
    return _f(a, b)

def tensor_matmul(a: Any, b: Any) -> Any:
    from agilang.ml import tensor_matmul as _f
    return _f(a, b)

def tensor_add(a: Any, b: Any) -> Any:
    from agilang.ml import tensor_add as _f
    return _f(a, b)

def tensor_sub(a: Any, b: Any) -> Any:
    from agilang.ml import tensor_sub as _f
    return _f(a, b)

def tensor_mul(a: Any, b: Any) -> Any:
    from agilang.ml import tensor_mul as _f
    return _f(a, b)

def tensor_mean(values: Any) -> float:
    from agilang.ml import tensor_mean as _f
    return _f(values)

def tensor_variance(values: Any) -> float:
    from agilang.ml import tensor_variance as _f
    return _f(values)

def tensor_relu(values: Any) -> Any:
    from agilang.ml import tensor_relu as _f
    return _f(values)

def tensor_sigmoid(values: Any) -> Any:
    from agilang.ml import tensor_sigmoid as _f
    return _f(values)

def tensor_softmax(values: Any) -> Any:
    from agilang.ml import tensor_softmax as _f
    return _f(values)

def ml_dataset_summary(rows: Any) -> Dict[str, Any]:
    from agilang.ml import ml_dataset_summary as _f
    return _f(rows)

def ml_train_test_split(rows: Any, test_ratio: float = 0.2, shuffle: bool = False, seed: int = 42) -> Dict[str, Any]:
    from agilang.ml import ml_train_test_split as _f
    return _f(rows, test_ratio=test_ratio, shuffle=shuffle, seed=seed)

def ml_linear_regression(rows: Any, target: str, features: Any) -> Dict[str, Any]:
    from agilang.ml import ml_linear_regression as _f
    return _f(rows, target, features)

def ml_predict_linear(model: Dict[str, Any], row: Dict[str, Any]) -> float:
    from agilang.ml import ml_predict_linear as _f
    return _f(model, row)

def ml_minmax_scale(rows: Any, columns: Any) -> Any:
    from agilang.ml import ml_minmax_scale as _f
    return _f(rows, columns)
