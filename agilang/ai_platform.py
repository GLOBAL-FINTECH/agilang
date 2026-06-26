"""AGILANG AIFlow production capability layer.

This module centralizes the truth about which AI features are production-ready,
which are CPU-reference, and which require optional external backends. It is
intended for CLI/API health checks and deployment gates.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from typing import Any

from .cuda_backend import native_gpu_status
from .distributed_runtime import distributed_capabilities
from .gpu_kernel_registry import backend_status, default_registry
from .model_exchange import onnx_bridge_status
from .onnx_tier1_runtime import onnx_runtime_status
from .torch_compat import torch_compat_status

AI_PLATFORM_FORMAT = "agilang-aiflow-platform-v1"


class AICapabilityError(RuntimeError):
    pass


def _available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


@dataclass(frozen=True)
class AICapability:
    name: str
    status: str
    production: bool
    backend: str
    notes: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def ai_capabilities() -> dict[str, Any]:
    """Return a deployment-grade capability report."""
    onnx_status = onnx_runtime_status()
    gpu_status = backend_status()
    native_gpu = native_gpu_status()
    caps = [
        AICapability("tokenizer", "available", True, "native-python", "BPE train/encode/decode/save/load"),
        AICapability("dense_mlp", "available", True, "native-python-cpu", "Small MLP training and inference with .agi-model persistence"),
        AICapability("cnn_classifier", "available", True, "native-python-cpu-reference", "Small CNN classifier training/inference; external backend recommended for high-volume workloads"),
        AICapability("transformer_runtime", "available", True, "native-python-cpu-reference", "Small transformer inference runtime; not GPT-scale training"),
        AICapability("llm_trainer", "available", True, "native-ngram", "Tokenizer-backed n-gram LM for small domain text workloads"),
        AICapability("torch_compat", "available", True, "agilang-native-ndtensor", "PyTorch-style API subset: Tensor, nn.Module, Linear, activations, SGD, save/load"),
        AICapability("pytorch_full_parity", "not_available", False, "multi-year-native-runtime", "Full PyTorch parity requires thousands of ops, dispatcher/autograd/compiler/CUDA/distributed/serialization parity"),
        AICapability("onnx_descriptor_runtime", "available", True, "native-python-cpu", "Descriptor graph executor for controlled graphs"),
        AICapability("onnx_model_runtime", "available" if onnx_status.get("onnxruntime_available") else "missing_optional_backend", bool(onnx_status.get("onnxruntime_available")), "onnxruntime", "Install onnxruntime/onnxruntime-gpu for real .onnx model files"),
        AICapability("gpu_dispatch", "available" if any(v.get("production") for k, v in gpu_status.items() if k != "cpu") else "cpu_fallback_only", True, "cpu/optional-gpu", "CPU kernels always available; GPU depends on torch/cupy/directml/mps or AGILANG native GPU library"),
        AICapability("native_gpu_backend", "available" if native_gpu.get("available") else "missing_native_library", bool(native_gpu.get("available")), "agilang-native-shared-library", str(native_gpu.get("reason") or "Native GPU library loaded")),
        AICapability("native_cuda_full_parity", "not_available", False, "agilang-native-cuda-roadmap", "Full native CUDA parity requires compiled kernels, allocator, streams, autograd integration and CI on GPU hardware"),
        AICapability("distributed_runtime", "available", True, "local/filesystem", "Local and shared-filesystem allreduce coordinator"),
    ]
    return {
        "format": AI_PLATFORM_FORMAT,
        "capabilities": [cap.as_dict() for cap in caps],
        "optional_packages": {
            "onnx": _available("onnx"),
            "onnxruntime": _available("onnxruntime"),
            "torch": _available("torch"),
            "cupy": _available("cupy"),
            "numpy": _available("numpy"),
        },
        "torch_compat": torch_compat_status(),
        "native_gpu": native_gpu,
        "onnx": onnx_bridge_status(),
        "gpu": default_registry().production_report(),
        "distributed": distributed_capabilities(),
    }


def require_ai_capability(name: str, *, production: bool = True) -> dict[str, Any]:
    report = ai_capabilities()
    for cap in report["capabilities"]:
        if cap["name"] == name:
            if production and not cap["production"]:
                raise AICapabilityError(f"AI capability is not production-ready: {name}. {cap['notes']}")
            return cap
    raise AICapabilityError(f"Unknown AI capability: {name}")


def ai_deployment_gate(*, require_onnxruntime: bool = False, require_gpu: bool = False, require_native_gpu: bool = False, require_full_torch_parity: bool = False) -> dict[str, Any]:
    report = ai_capabilities()
    errors: list[str] = []
    if require_onnxruntime and not report["onnx"].get("onnxruntime_available"):
        errors.append("onnxruntime is required but not installed")
    if require_gpu and not any(v.get("production") for k, v in report["gpu"]["backends"].items() if k != "cpu"):
        errors.append("GPU backend is required but no production GPU backend is available")
    if require_native_gpu and not report["native_gpu"].get("available"):
        errors.append("AGILANG native GPU shared library is required but unavailable")
    if require_full_torch_parity:
        errors.append("Full PyTorch parity is not available; use torch_compat subset or external PyTorch backend")
    return {"ok": not errors, "errors": errors, "report": report}


__all__ = ["AI_PLATFORM_FORMAT", "AICapability", "AICapabilityError", "ai_capabilities", "require_ai_capability", "ai_deployment_gate"]
