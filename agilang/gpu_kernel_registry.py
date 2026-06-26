"""GPU kernel registry scaffold for AGILANG AIFlow.

This defines kernel names, backend support, and dispatch status. Native CUDA,
ROCm, DirectML, and Metal implementations can register behind this stable API.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class KernelSpec:
    name: str
    backend: str
    status: str = "planned"
    fn: Callable[..., Any] | None = None


class GPUKernelRegistry:
    def __init__(self) -> None:
        self.kernels: dict[str, KernelSpec] = {}

    def register(self, name: str, backend: str, status: str = "planned", fn: Callable[..., Any] | None = None) -> None:
        self.kernels[f"{backend}:{name}"] = KernelSpec(name, backend, status, fn)

    def available(self) -> list[dict[str, str]]:
        return [{"name": k.name, "backend": k.backend, "status": k.status} for k in self.kernels.values()]

    def dispatch(self, name: str, backend: str, *args: Any, **kwargs: Any) -> Any:
        spec = self.kernels.get(f"{backend}:{name}")
        if spec is None:
            raise KeyError(f"kernel not registered: {backend}:{name}")
        if spec.fn is None:
            raise NotImplementedError(f"kernel registered but no native implementation yet: {backend}:{name}")
        return spec.fn(*args, **kwargs)


def default_registry() -> GPUKernelRegistry:
    reg = GPUKernelRegistry()
    for backend in ["cuda", "rocm", "directml", "metal"]:
        for name in ["matmul", "conv2d", "relu", "softmax", "attention"]:
            reg.register(name, backend)
    return reg


__all__ = ["KernelSpec", "GPUKernelRegistry", "default_registry"]
