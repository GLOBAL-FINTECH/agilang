"""GPU runtime planner for AGILANG AIFlow.

This module does not claim production GPU kernels. It defines selection policy
and backend planning for CUDA, ROCm, DirectML, Metal, and CPU fallback.
"""
from __future__ import annotations

import platform
import shutil
from typing import Any


def detect_gpu_backends() -> dict[str, Any]:
    return {
        "cuda": {"available": bool(shutil.which("nvidia-smi")), "min_vram_gb": 2},
        "rocm": {"available": bool(shutil.which("rocm-smi")), "min_vram_gb": 2},
        "directml": {"available": platform.system().lower() == "windows", "min_vram_gb": 2},
        "metal": {"available": platform.system().lower() == "darwin", "min_vram_gb": 2},
        "cpu": {"available": True},
    }


def select_accelerator(prefer: str = "auto") -> dict[str, Any]:
    backends = detect_gpu_backends()
    if prefer != "auto" and prefer in backends and backends[prefer]["available"]:
        return {"backend": prefer, "status": "planned", "kernels": "pending_native_kernel_implementation"}
    for name in ["cuda", "rocm", "directml", "metal"]:
        if backends[name]["available"]:
            return {"backend": name, "status": "planned", "kernels": "pending_native_kernel_implementation"}
    return {"backend": "cpu", "status": "active_reference_backend"}


__all__ = ["detect_gpu_backends", "select_accelerator"]
