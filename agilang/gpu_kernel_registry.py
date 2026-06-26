"""Production-facing kernel registry for AGILANG AIFlow.

The old module only registered planned GPU kernels. This version keeps GPU
registration, adds backend detection, provides CPU fallback kernels, and exposes
clear dispatch semantics. GPU acceleration is used only when an installed backend
actually supports it; otherwise calls fail clearly or fall back to CPU by policy.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import math
from typing import Callable, Any, Sequence


class KernelBackendUnavailable(RuntimeError):
    pass


@dataclass
class KernelSpec:
    name: str
    backend: str
    status: str = "planned"
    fn: Callable[..., Any] | None = None
    production: bool = False
    notes: str = ""


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def backend_status() -> dict[str, dict[str, Any]]:
    status: dict[str, dict[str, Any]] = {
        "cpu": {"available": True, "production": True, "package": None},
        "cuda": {"available": False, "production": False, "package": "torch/cupy"},
        "rocm": {"available": False, "production": False, "package": "torch"},
        "directml": {"available": _module_available("torch_directml"), "production": _module_available("torch_directml"), "package": "torch-directml"},
        "metal": {"available": False, "production": False, "package": "torch mps"},
    }
    if _module_available("torch"):
        try:
            import torch  # type: ignore
            status["cuda"]["available"] = bool(torch.cuda.is_available())
            status["cuda"]["production"] = bool(torch.cuda.is_available())
            status["rocm"]["available"] = bool(getattr(torch.version, "hip", None))
            status["rocm"]["production"] = bool(getattr(torch.version, "hip", None))
            status["metal"]["available"] = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
            status["metal"]["production"] = bool(status["metal"]["available"])
        except Exception:
            pass
    if _module_available("cupy"):
        status["cuda"]["available"] = True
        status["cuda"]["production"] = True
        status["cuda"]["package"] = "cupy"
    return status


# ---------------------------------------------------------------------------
# CPU fallback kernels
# ---------------------------------------------------------------------------

def cpu_matmul(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> list[list[float]]:
    if not a or not b:
        return []
    if len(a[0]) != len(b):
        raise ValueError("matmul shape mismatch")
    return [[sum(float(row[k]) * float(b[k][j]) for k in range(len(b))) for j in range(len(b[0]))] for row in a]


def cpu_relu(x: Any) -> Any:
    if isinstance(x, list):
        return [cpu_relu(v) for v in x]
    return max(0.0, float(x))


def cpu_softmax(values: Sequence[float]) -> list[float]:
    vals = [float(v) for v in values]
    if not vals:
        return []
    top = max(vals)
    exps = [math.exp(v - top) for v in vals]
    total = sum(exps) or 1.0
    return [v / total for v in exps]


def cpu_conv2d(image: Sequence[Sequence[float]], kernel: Sequence[Sequence[float]], bias: float = 0.0, stride: int = 1) -> list[list[float]]:
    if stride <= 0:
        raise ValueError("stride must be positive")
    h, w = len(image), len(image[0]) if image else 0
    kh, kw = len(kernel), len(kernel[0]) if kernel else 0
    if h < kh or w < kw:
        return []
    out: list[list[float]] = []
    for i in range(0, h - kh + 1, stride):
        row: list[float] = []
        for j in range(0, w - kw + 1, stride):
            total = float(bias)
            for ki in range(kh):
                for kj in range(kw):
                    total += float(image[i + ki][j + kj]) * float(kernel[ki][kj])
            row.append(total)
        out.append(row)
    return out


def _torch_dispatch(name: str, *args: Any, device: str = "cuda", **kwargs: Any) -> Any:
    import torch  # type: ignore
    if device == "cuda" and not torch.cuda.is_available():
        raise KernelBackendUnavailable("CUDA is not available through torch")
    if device == "mps" and not (getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()):
        raise KernelBackendUnavailable("Metal/MPS is not available through torch")
    if name == "matmul":
        a = torch.tensor(args[0], dtype=torch.float32, device=device)
        b = torch.tensor(args[1], dtype=torch.float32, device=device)
        return torch.matmul(a, b).detach().cpu().tolist()
    if name == "relu":
        x = torch.tensor(args[0], dtype=torch.float32, device=device)
        return torch.relu(x).detach().cpu().tolist()
    if name == "softmax":
        x = torch.tensor(args[0], dtype=torch.float32, device=device)
        return torch.softmax(x, dim=-1).detach().cpu().tolist()
    raise NotImplementedError(f"torch backend does not implement kernel: {name}")


class GPUKernelRegistry:
    def __init__(self) -> None:
        self.kernels: dict[str, KernelSpec] = {}

    def register(self, name: str, backend: str, status: str = "planned", fn: Callable[..., Any] | None = None, *, production: bool = False, notes: str = "") -> None:
        self.kernels[f"{backend}:{name}"] = KernelSpec(name, backend, status, fn, production=production, notes=notes)

    def available(self) -> list[dict[str, Any]]:
        return [spec.__dict__.copy() | {"has_function": spec.fn is not None} for spec in self.kernels.values()]

    def backends(self) -> dict[str, dict[str, Any]]:
        return backend_status()

    def dispatch(self, name: str, backend: str = "auto", *args: Any, allow_cpu_fallback: bool = True, **kwargs: Any) -> Any:
        selected = self.select_backend(name, backend=backend, allow_cpu_fallback=allow_cpu_fallback)
        spec = self.kernels.get(f"{selected}:{name}")
        if spec is None:
            raise KeyError(f"kernel not registered: {selected}:{name}")
        if spec.fn is None:
            raise NotImplementedError(f"kernel registered but no implementation yet: {selected}:{name}")
        return spec.fn(*args, **kwargs)

    def select_backend(self, name: str, *, backend: str = "auto", allow_cpu_fallback: bool = True) -> str:
        if backend != "auto":
            status = backend_status().get(backend, {"available": False})
            if not status.get("available") and backend != "cpu":
                if allow_cpu_fallback:
                    return "cpu"
                raise KernelBackendUnavailable(f"backend unavailable: {backend}")
            return backend
        status = backend_status()
        for candidate in ["cuda", "rocm", "metal", "directml"]:
            if status.get(candidate, {}).get("available") and f"{candidate}:{name}" in self.kernels:
                spec = self.kernels[f"{candidate}:{name}"]
                if spec.fn is not None:
                    return candidate
        if allow_cpu_fallback:
            return "cpu"
        raise KernelBackendUnavailable(f"no accelerated backend available for kernel: {name}")

    def production_report(self) -> dict[str, Any]:
        return {"backends": self.backends(), "kernels": self.available()}


def default_registry() -> GPUKernelRegistry:
    reg = GPUKernelRegistry()
    reg.register("matmul", "cpu", "available", cpu_matmul, production=True, notes="dependency-free CPU fallback")
    reg.register("relu", "cpu", "available", cpu_relu, production=True, notes="dependency-free CPU fallback")
    reg.register("softmax", "cpu", "available", cpu_softmax, production=True, notes="dependency-free CPU fallback")
    reg.register("conv2d", "cpu", "available", cpu_conv2d, production=True, notes="dependency-free CPU fallback")
    reg.register("attention", "cpu", "planned", None, production=False, notes="use transformer_runtime for attention")

    if _module_available("torch"):
        reg.register("matmul", "cuda", "available_if_device_present", lambda *a, **kw: _torch_dispatch("matmul", *a, device="cuda", **kw), production=True, notes="torch CUDA dispatch")
        reg.register("relu", "cuda", "available_if_device_present", lambda *a, **kw: _torch_dispatch("relu", *a, device="cuda", **kw), production=True, notes="torch CUDA dispatch")
        reg.register("softmax", "cuda", "available_if_device_present", lambda *a, **kw: _torch_dispatch("softmax", *a, device="cuda", **kw), production=True, notes="torch CUDA dispatch")
        reg.register("matmul", "metal", "available_if_device_present", lambda *a, **kw: _torch_dispatch("matmul", *a, device="mps", **kw), production=True, notes="torch MPS dispatch")
        reg.register("relu", "metal", "available_if_device_present", lambda *a, **kw: _torch_dispatch("relu", *a, device="mps", **kw), production=True, notes="torch MPS dispatch")
        reg.register("softmax", "metal", "available_if_device_present", lambda *a, **kw: _torch_dispatch("softmax", *a, device="mps", **kw), production=True, notes="torch MPS dispatch")

    for backend in ["rocm", "directml"]:
        for name in ["matmul", "conv2d", "relu", "softmax", "attention"]:
            if f"{backend}:{name}" not in reg.kernels:
                reg.register(name, backend, "planned", None, production=False)
    return reg


def dispatch_kernel(name: str, *args: Any, backend: str = "auto", allow_cpu_fallback: bool = True, **kwargs: Any) -> Any:
    return default_registry().dispatch(name, backend, *args, allow_cpu_fallback=allow_cpu_fallback, **kwargs)


__all__ = [
    "KernelSpec",
    "KernelBackendUnavailable",
    "GPUKernelRegistry",
    "backend_status",
    "default_registry",
    "dispatch_kernel",
    "cpu_matmul",
    "cpu_relu",
    "cpu_softmax",
    "cpu_conv2d",
]
