"""AGILANG AIFlow production capability layer.

This module centralizes the truth about which AI features are production-ready,
which are CPU-reference, and which require optional external backends. It is
intended for CLI/API health checks and deployment gates.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from typing import Any

from .bpe_tokenizer import BPETokenizer
from .distributed_runtime import distributed_capabilities
from .gpu_kernel_registry import backend_status, default_registry
from .model_exchange import onnx_bridge_status
from .onnx_tier1_runtime import onnx_runtime_status

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
    caps = [
        AICapability("tokenizer", "available", True, "native-python", "BPE train/encode/decode/save/load"),
        AICapability("dense_mlp", "available", True, "native-python-cpu", "Small MLP training and inference with .agi-model persistence"),
        AICapability("cnn_classifier", "available", True, "native-python-cpu-reference", "Small CNN classifier training/inference; use external backend for high-volume workloads"),
        AICapability("transformer_runtime", "available", True, "native-python-cpu-reference", "Small transformer inference runtime; not GPT-scale training"),
        AICapability("llm_trainer", "available", True, "native-ngram", "Tokenizer-backed n-gram LM for small domain text workloads"),
        AICapability("onnx_descriptor_runtime", "available", True, "native-python-cpu", "Descriptor graph executor for controlled graphs"),
        AICapability("onnx_model_runtime", "available" if onnx_status.get("onnxruntime_available") else "missing_optional_backend", bool(onnx_status.get("onnxruntime_available")), "onnxruntime", "Install onnxruntime/onnxruntime-gpu for real .onnx model files"),
        AICapability("gpu_dispatch", "available" if any(v.get("production") for k, v in gpu_status.items() if k != "cpu") else "cpu_fallback_only", True, "cpu/optional-gpu", "CPU kernels always available; GPU depends on torch/cupy/directml/mps"),
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


def ai_deployment_gate(*, require_onnxruntime: bool = False, require_gpu: bool = False) -> dict[str, Any]:
    report = ai_capabilities()
    errors: list[str] = []
    if require_onnxruntime and not report["onnx"].get("onnxruntime_available"):
        errors.append("onnxruntime is required but not installed")
    if require_gpu and not any(v.get("production") for k, v in report["gpu"]["backends"].items() if k != "cpu"):
        errors.append("GPU backend is required but no production GPU backend is available")
    return {"ok": not errors, "errors": errors, "report": report}


__all__ = ["AI_PLATFORM_FORMAT", "AICapability", "AICapabilityError", "ai_capabilities", "require_ai_capability", "ai_deployment_gate"]
