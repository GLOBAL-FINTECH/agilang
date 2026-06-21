"""AGILANG v1.7 native hybrid web/mobile runtime.

This module cross-integrates AGILANG's Python web/realtime runtime with the
native C HTTP/WebSocket runtime.  The Python backend remains the feature-complete
application runtime, while the C runtime provides a native edge/transport ABI
that can be loaded from bundled precompiled artifacts, compiled locally when needed, and used as the foundation for
future fully-native lowering of AGILANG web primitives.
"""

from __future__ import annotations

import ctypes
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


RUNTIME_VERSION = "1.9.3"


@dataclass
class NativeBuildResult:
    """Result returned after compiling the native C runtime."""

    ok: bool
    library_path: Path | None = None
    command: list[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "library_path": str(self.library_path) if self.library_path else None,
            "command": self.command,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "returncode": self.returncode,
        }


class NativeRuntimeLoadError(RuntimeError):
    """Raised when the native C runtime cannot be loaded."""


def _package_native_dir() -> Path:
    return Path(__file__).resolve().parent / "native"


def _project_native_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "native"


def native_source_paths() -> dict[str, Path]:
    """Return the C/H source paths for the native runtime.

    Prefer package data so installed wheels can still build the runtime.  Fall
    back to the repository-level native/ directory for source checkouts.
    """

    candidates = [_package_native_dir(), _project_native_dir()]
    for base in candidates:
        c_file = base / "agilang_net_runtime.c"
        h_file = base / "agilang_net_runtime.h"
        if c_file.exists() and h_file.exists():
            return {"base": base, "c": c_file, "h": h_file}
    raise FileNotFoundError("Could not locate agilang_net_runtime.c/h")


def _shared_name() -> str:
    system = platform.system().lower()
    if system.startswith("win"):
        return "agilang_net_runtime.dll"
    if system == "darwin":
        return "libagilang_net_runtime.dylib"
    return "libagilang_net_runtime.so"


def _platform_tag() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower().replace("amd64", "x86_64")
    if machine in {"x64", "x86-64"}:
        machine = "x86_64"
    if system.startswith("linux"):
        return f"linux-{machine}"
    if system == "darwin":
        return f"macos-{machine}"
    if system.startswith("win"):
        return f"windows-{machine}"
    return f"{system}-{machine}"


def prebuilt_native_dir(platform_tag: str | None = None) -> Path:
    """Return the bundled prebuilt runtime directory for a platform tag."""

    return _package_native_dir() / "prebuilt" / (platform_tag or _platform_tag())


def bundled_prebuilt_runtime(platform_tag: str | None = None) -> Path | None:
    """Return the bundled precompiled shared library for this platform, if present."""

    candidate = prebuilt_native_dir(platform_tag) / _shared_name()
    return candidate if candidate.exists() else None


def bundled_prebuilt_artifacts(platform_tag: str | None = None) -> dict[str, str]:
    """List bundled precompiled runtime artifacts for the requested/current platform."""

    base = prebuilt_native_dir(platform_tag)
    if not base.exists():
        return {}
    artifacts: dict[str, str] = {}
    for item in sorted(base.iterdir()):
        if item.is_file():
            artifacts[item.name] = str(item)
    return artifacts


def installed_prebuilt_runtime(output_dir: str | Path | None = None) -> Path | None:
    """Copy the bundled prebuilt shared runtime into the runtime cache/build dir.

    This makes deployments work on machines without a compiler when a matching
    bundled artifact is available. Returns the installed library path, or None
    when no matching bundled library exists.
    """

    src = bundled_prebuilt_runtime()
    if src is None:
        return None
    out_dir = Path(output_dir).expanduser().resolve() if output_dir else default_native_build_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / _shared_name()
    shutil.copy2(src, dst)
    return dst


def default_native_build_dir() -> Path:
    """Return a stable build directory under the user's cache/temp area."""

    configured = os.environ.get("AGILANG_NATIVE_BUILD_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(tempfile.gettempdir()) / "agilang-native-runtime" / RUNTIME_VERSION


def compile_native_runtime(
    output_dir: str | Path | None = None,
    *,
    cc: str | None = None,
    optimize: bool = True,
    extra_cflags: list[str] | None = None,
) -> NativeBuildResult:
    """Compile the AGILANG native C HTTP/WebSocket runtime as a shared library.

    The returned library can be loaded by :func:`load_native_runtime` and used by
    Python/AGILANG code through ctypes.  This is the core cross-integration layer
    between the Python application runtime and the native C transport runtime.
    """

    paths = native_source_paths()
    out_dir = Path(output_dir).expanduser().resolve() if output_dir else default_native_build_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    lib_path = out_dir / _shared_name()
    compiler = cc or os.environ.get("CC") or shutil.which("gcc") or shutil.which("clang") or "gcc"
    system = platform.system().lower()
    cmd = [compiler, "-std=c11", "-Wall", "-Wextra"]
    if optimize:
        cmd.append("-O2")
    if system.startswith("win"):
        cmd += [str(paths["c"]), "-shared", "-o", str(lib_path), "-lws2_32"]
    else:
        cmd += ["-fPIC", "-shared", str(paths["c"]), "-o", str(lib_path), "-pthread"]
    if extra_cflags:
        cmd[1:1] = extra_cflags
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as exc:
        return NativeBuildResult(
            ok=False,
            library_path=None,
            command=cmd,
            stdout="",
            stderr=f"C compiler not found: {exc}",
            returncode=127,
        )
    return NativeBuildResult(
        ok=proc.returncode == 0 and lib_path.exists(),
        library_path=lib_path if lib_path.exists() else None,
        command=cmd,
        stdout=proc.stdout,
        stderr=proc.stderr,
        returncode=proc.returncode,
    )


class NativeNetRuntime:
    """ctypes wrapper around the compiled AGILANG native C runtime."""

    def __init__(
        self,
        library_path: str | Path | None = None,
        *,
        auto_build: bool = True,
        prefer_prebuilt: bool = True,
    ):
        if library_path:
            self.library_path = Path(library_path).resolve()
        else:
            self.library_path = default_native_build_dir() / _shared_name()
            if not self.library_path.exists() and prefer_prebuilt:
                installed = installed_prebuilt_runtime(self.library_path.parent)
                if installed is not None:
                    self.library_path = installed
        if not self.library_path.exists() and auto_build:
            result = compile_native_runtime(self.library_path.parent)
            if not result.ok:
                prebuilt = bundled_prebuilt_runtime()
                hint = f" No bundled prebuilt runtime for {_platform_tag()} was found." if prebuilt is None else f" Bundled prebuilt runtime was available at {prebuilt}."
                raise NativeRuntimeLoadError(f"Native runtime build failed: {result.stderr or result.stdout}.{hint}")
            self.library_path = result.library_path or self.library_path
        if not self.library_path.exists():
            raise NativeRuntimeLoadError(f"Native runtime library not found: {self.library_path}")
        self.lib = ctypes.CDLL(str(self.library_path))
        self._configure_abi()

    def _configure_abi(self) -> None:
        self.lib.agi_net_runtime_version.restype = ctypes.c_char_p
        self.lib.agi_net_runtime_capabilities.restype = ctypes.c_char_p
        self.lib.agi_net_runtime_selftest.restype = ctypes.c_int
        self.lib.agi_ws_broadcast.argtypes = [ctypes.c_char_p]
        self.lib.agi_ws_broadcast.restype = ctypes.c_int

    def version(self) -> str:
        return self.lib.agi_net_runtime_version().decode("utf-8")

    def capabilities(self) -> dict[str, Any]:
        raw = self.lib.agi_net_runtime_capabilities().decode("utf-8")
        return json.loads(raw)

    def selftest(self) -> bool:
        return int(self.lib.agi_net_runtime_selftest()) == 0

    def broadcast_default(self, message: str) -> int:
        return int(self.lib.agi_ws_broadcast(message.encode("utf-8")))


def native_runtime_available() -> bool:
    """Return True when the C runtime can be compiled and loaded."""

    try:
        rt = NativeNetRuntime(auto_build=True)
        return rt.selftest()
    except Exception:
        return False


def native_runtime_status(build: bool = False) -> dict[str, Any]:
    """Return a diagnostic status object for the native runtime."""

    status: dict[str, Any] = {
        "agilang_runtime_version": RUNTIME_VERSION,
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "sources": {k: str(v) for k, v in native_source_paths().items()},
        "library_name": _shared_name(),
        "platform_tag": _platform_tag(),
        "default_build_dir": str(default_native_build_dir()),
        "bundled_prebuilt_library": str(bundled_prebuilt_runtime()) if bundled_prebuilt_runtime() else None,
        "bundled_prebuilt_artifacts": bundled_prebuilt_artifacts(),
        "compiler": os.environ.get("CC") or shutil.which("gcc") or shutil.which("clang"),
    }
    if build:
        result = compile_native_runtime()
        status["build"] = result.as_dict()
    lib = default_native_build_dir() / _shared_name()
    status["library_exists"] = lib.exists()
    if lib.exists():
        try:
            rt = NativeNetRuntime(lib, auto_build=False)
            status["native_version"] = rt.version()
            status["native_capabilities"] = rt.capabilities()
            status["native_selftest"] = rt.selftest()
        except Exception as exc:
            status["load_error"] = str(exc)
    return status


class HybridWebRuntime:
    """Runtime selector for Python, C-native, and hybrid web deployment.

    Modes:
    - ``python``: use AGILANG's Python WebApp runtime only.
    - ``native-c``: build/load the native C transport runtime only.
    - ``hybrid``: expose both; Python serves full framework apps while C runtime
      provides native HTTP/WebSocket transport ABI and compile/load diagnostics.
    """

    def __init__(self, mode: str = "hybrid", *, auto_build_native: bool = False):
        normalized = mode.replace("_", "-").lower()
        if normalized not in {"python", "native-c", "c", "hybrid"}:
            raise ValueError("mode must be 'python', 'native-c', or 'hybrid'")
        self.mode = "native-c" if normalized == "c" else normalized
        self.native: NativeNetRuntime | None = None
        if self.mode in {"native-c", "hybrid"} and auto_build_native:
            self.native = NativeNetRuntime(auto_build=True)

    def build_native(self, output_dir: str | Path | None = None, *, cc: str | None = None) -> NativeBuildResult:
        result = compile_native_runtime(output_dir, cc=cc)
        if result.ok and result.library_path:
            self.native = NativeNetRuntime(result.library_path, auto_build=False)
        return result

    def load_native(self, library_path: str | Path | None = None) -> NativeNetRuntime:
        self.native = NativeNetRuntime(library_path, auto_build=True)
        return self.native

    def capabilities(self) -> dict[str, Any]:
        native_caps: dict[str, Any] | None = None
        native_ok = False
        if self.native is not None:
            native_ok = self.native.selftest()
            native_caps = self.native.capabilities()
        return {
            "mode": self.mode,
            "python_http": self.mode in {"python", "hybrid"},
            "python_websocket": self.mode in {"python", "hybrid"},
            "python_webrtc_signaling": self.mode in {"python", "hybrid"},
            "c_http": self.mode in {"native-c", "hybrid"},
            "c_websocket": self.mode in {"native-c", "hybrid"},
            "c_loaded": self.native is not None,
            "c_selftest": native_ok,
            "c_capabilities": native_caps,
            "cross_integration": "ctypes ABI bridge + shared C runtime + Python web framework",
        }

    def serve_python_app(self, app: Any, host: str = "127.0.0.1", port: int = 8000) -> Any:
        """Serve a full AGILANG Python WebApp using the Python runtime."""

        if self.mode == "native-c":
            raise RuntimeError("native-c mode cannot serve Python WebApp objects; use hybrid or python mode")
        if not hasattr(app, "listen"):
            raise TypeError("Expected an AGILANG WebApp with .listen(host, port)")
        return app.listen(host, port)

    def status(self) -> dict[str, Any]:
        payload = native_runtime_status(build=False)
        payload["hybrid"] = self.capabilities()
        return payload


def hybrid_web_runtime(mode: str = "hybrid", *, auto_build_native: bool = False) -> HybridWebRuntime:
    return HybridWebRuntime(mode, auto_build_native=auto_build_native)


def native_web_runtime(*, auto_build: bool = True, prefer_prebuilt: bool = True) -> NativeNetRuntime:
    return NativeNetRuntime(auto_build=auto_build, prefer_prebuilt=prefer_prebuilt)


def native_prebuilt_runtime_install(output_dir: str | Path | None = None) -> Path | None:
    return installed_prebuilt_runtime(output_dir)


def native_prebuilt_status() -> dict[str, Any]:
    return {
        "platform_tag": _platform_tag(),
        "library_name": _shared_name(),
        "bundled_library": str(bundled_prebuilt_runtime()) if bundled_prebuilt_runtime() else None,
        "artifacts": bundled_prebuilt_artifacts(),
    }


# AGILAB aliases requested by the project owner.  AGILANG remains the language
# name; AGILAB can be used as the branded platform/runtime name in apps.
def agilab_web_runtime(mode: str = "hybrid", *, auto_build_native: bool = False) -> HybridWebRuntime:
    return hybrid_web_runtime(mode, auto_build_native=auto_build_native)


def agilab_native_runtime(*, auto_build: bool = True) -> NativeNetRuntime:
    return native_web_runtime(auto_build=auto_build)

# --- v1.5 cross-platform runtime support matrix ---
SUPPORTED_NATIVE_PLATFORMS = {
    "linux-x86_64": {
        "library_name": "libagilang_net_runtime.so",
        "ci_runner": "ubuntu-latest",
        "status": "bundled-when-built-on-linux",
        "notes": "Linux x86_64 shared/static/object artifacts are included when built from this environment or CI.",
    },
    "windows-x86_64": {
        "library_name": "agilang_net_runtime.dll",
        "ci_runner": "windows-latest",
        "status": "release-workflow-supported",
        "notes": "Built by GitHub Actions on Windows and packaged into agilang/native/prebuilt/windows-x86_64.",
    },
    "macos-x86_64": {
        "library_name": "libagilang_net_runtime.dylib",
        "ci_runner": "macos-13",
        "status": "release-workflow-supported",
        "notes": "Built by GitHub Actions on Intel macOS and packaged into agilang/native/prebuilt/macos-x86_64.",
    },
    "macos-arm64": {
        "library_name": "libagilang_net_runtime.dylib",
        "ci_runner": "macos-latest",
        "status": "release-workflow-supported",
        "notes": "Built by GitHub Actions on Apple Silicon macOS and packaged into agilang/native/prebuilt/macos-arm64.",
    },
    "android-arm64-v8a": {
        "library_name": "libagilang_net_runtime.so",
        "ci_runner": "ubuntu-latest + Android NDK",
        "status": "mobile-source-and-ci-supported",
        "notes": "Android shared library target for physical devices through the mobile native bridge.",
    },
    "android-x86_64": {
        "library_name": "libagilang_net_runtime.so",
        "ci_runner": "ubuntu-latest + Android NDK",
        "status": "mobile-source-and-ci-supported",
        "notes": "Android shared library target for emulator/x86_64 devices through the mobile native bridge.",
    },
    "ios-arm64": {
        "library_name": "libagilang_net_runtime.a",
        "ci_runner": "macos-latest + Xcode",
        "status": "mobile-source-and-ci-supported",
        "notes": "iOS static library target for physical iPhone/iPad devices.",
    },
    "ios-simulator-arm64": {
        "library_name": "libagilang_net_runtime.a",
        "ci_runner": "macos-latest + Xcode",
        "status": "mobile-source-and-ci-supported",
        "notes": "iOS static library target for Apple Silicon Simulator.",
    },
}


def native_platform_matrix() -> dict[str, Any]:
    """Return cross-platform runtime capability and artifact availability.

    This intentionally distinguishes **supported release targets** from
    **artifacts physically bundled in the current zip/wheel**. The package can
    only contain real Windows/macOS binaries after the release workflow has run
    on those operating systems; AGILANG does not fake binaries for platforms it
    cannot compile on the current host.
    """

    platforms: dict[str, Any] = {}
    for tag, meta in SUPPORTED_NATIVE_PLATFORMS.items():
        base = prebuilt_native_dir(tag)
        artifacts = bundled_prebuilt_artifacts(tag)
        expected = base / meta["library_name"]
        platforms[tag] = {
            **meta,
            "prebuilt_dir": str(base),
            "shared_library": str(expected),
            "shared_library_bundled": expected.exists(),
            "artifacts": artifacts,
        }
    return {
        "current_platform_tag": _platform_tag(),
        "current_library_name": _shared_name(),
        "runtime_version": RUNTIME_VERSION,
        "supported_platforms": platforms,
        "loading_order": [
            "developer_supplied_library_path",
            "cached_installed_runtime",
            "bundled_platform_prebuilt",
            "local_c_compilation_fallback",
        ],
        "mobile_note": "Android/iOS targets are bridge/source and CI targets. Physical binaries are packaged only after platform toolchains build them.",
    }
