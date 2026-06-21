"""AGILANG v1.7 interop and capability package bridge.

AGILANG should be general-purpose, not locked to web apps.  This module lets an
AGILANG program import existing Python packages and load C shared libraries while
keeping a clean capability-reporting surface for precompiled packs.
"""
from __future__ import annotations

import ctypes
import importlib
import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any

INTEROP_VERSION = "1.7.0"


@dataclass
class PythonPackageHandle:
    name: str
    module: Any

    def call(self, function_name: str, *args: Any, **kwargs: Any) -> Any:
        target = self.module
        for part in function_name.split("."):
            target = getattr(target, part)
        return target(*args, **kwargs)

    def has(self, symbol: str) -> bool:
        target = self.module
        try:
            for part in symbol.split("."):
                target = getattr(target, part)
            return True
        except AttributeError:
            return False


@dataclass
class NativeLibraryHandle:
    path: str
    library: Any

    def symbol_exists(self, symbol: str) -> bool:
        try:
            getattr(self.library, symbol)
            return True
        except AttributeError:
            return False

    def raw(self) -> Any:
        return self.library


def python_package(name: str, required: bool = True) -> PythonPackageHandle | None:
    try:
        module = importlib.import_module(name)
        return PythonPackageHandle(name=name, module=module)
    except Exception as exc:
        if required:
            raise ImportError(f"Python package is not available: {name}") from exc
        return None


def python_package_status(names: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name in names:
        try:
            module = importlib.import_module(name)
            result[name] = {"installed": True, "version": getattr(module, "__version__", None)}
        except Exception as exc:
            result[name] = {"installed": False, "error": exc.__class__.__name__}
    return result


def native_library(path: str) -> NativeLibraryHandle:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"native library not found: {p}")
    return NativeLibraryHandle(str(p), ctypes.CDLL(str(p)))


def capability_manifest(path: str) -> dict[str, Any]:
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def interop_capabilities() -> dict[str, Any]:
    return {
        "version": INTEROP_VERSION,
        "python_package_import": True,
        "ctypes_native_library_load": True,
        "capability_manifest": True,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "precompiled_package_strategy": [
            "ship source-level AGILANG API",
            "ship Python adapter when available",
            "ship C shared library/static archive for speed-critical modules",
            "load via ctypes/native bridge",
            "fallback to Python implementation when native artifact is unavailable",
        ],
    }


def systems_capabilities() -> dict[str, Any]:
    from agilang.lowlevel_network import lowlevel_network_capabilities
    from agilang.evm import evm_capabilities
    from agilang.zk import zk_capabilities
    from agilang.blockchain import blockchain_capabilities

    return {
        "agilang_general_language": True,
        "not_web_only": True,
        "low_level_networking": lowlevel_network_capabilities(),
        "evm": evm_capabilities(),
        "zero_knowledge": zk_capabilities(),
        "blockchain_framework": blockchain_capabilities(),
        "interop": interop_capabilities(),
        "supported_app_types": ["cli", "web", "api", "realtime", "mobile-client", "native-bridge", "blockchain-framework", "zero-knowledge-tooling", "systems-prototype"],
    }
