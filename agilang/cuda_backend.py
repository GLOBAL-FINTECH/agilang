"""AGILANG GPU backend discovery layer.

This module detects whether an AGILANG native GPU shared library is present and
provides a stable status object for deployment gates. Actual accelerator source
files can be added in environments where repository write policies allow them.
"""
from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CUDA_BACKEND_FORMAT = "agilang-native-gpu-backend-v1"


class NativeGPUUnavailable(RuntimeError):
    pass


@dataclass
class NativeGPUStatus:
    available: bool
    library_path: str | None
    backend: str = "native-shared-library"
    format: str = CUDA_BACKEND_FORMAT
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def candidate_library_paths() -> list[Path]:
    paths: list[Path] = []
    env = os.environ.get("AGILANG_GPU_LIBRARY") or os.environ.get("AGILANG_CUDA_LIBRARY")
    if env:
        paths.append(Path(env))
    root = Path(__file__).resolve().parent
    paths.extend([
        root / "native" / "cuda" / "libagilang_cuda.so",
        root / "native" / "cuda" / "agilang_cuda.dll",
        root / "native" / "cuda" / "libagilang_cuda.dylib",
    ])
    return paths


def native_gpu_status() -> dict[str, Any]:
    for path in candidate_library_paths():
        if path.exists():
            try:
                ctypes.CDLL(str(path))
                return NativeGPUStatus(True, str(path)).as_dict()
            except Exception as exc:
                return NativeGPUStatus(False, str(path), reason=str(exc)).as_dict()
    return NativeGPUStatus(False, None, reason="No AGILANG native GPU shared library found").as_dict()


def require_native_gpu() -> None:
    status = native_gpu_status()
    if not status.get("available"):
        raise NativeGPUUnavailable(str(status.get("reason") or "Native GPU backend unavailable"))


__all__ = ["CUDA_BACKEND_FORMAT", "NativeGPUUnavailable", "NativeGPUStatus", "candidate_library_paths", "native_gpu_status", "require_native_gpu"]
