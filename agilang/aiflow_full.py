"""AIFlow full replacement architecture layer.

This module expands AGILANG AIFlow toward a TensorFlow replacement architecture.
It provides dependency-light primitives that can run today and clear extension
points for native GPU/C/WASM kernels later.
"""
from __future__ import annotations

import json
import math
import random
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence


@dataclass
class Variable:
    value: float
    grad: float = 0.0
    name: str | None = None

    def assign(self, value: float) -> None:
        self.value = float(value)

    def zero_grad(self) -> None:
        self.grad = 0.0


class GradientTape:
    """Small scalar autodiff-style tape for AGILANG starter models."""

    def gradient(self, loss: Callable[[], float], variables: Sequence[Variable], eps: float = 1e-5) -> list[float]:
        grads = []
        for var in variables:
            old = var.value
            var.value = old + eps
            plus = float(loss())
            var.value = old - eps
            minus = float(loss())
            var.value = old
            var.grad = (plus - minus) / (2 * eps)
            grads.append(var.grad)
        return grads


class Adam:
    def __init__(self, learning_rate: float = 0.001, beta1: float = 0.9, beta2: float = 0.999, epsilon: float = 1e-8) -> None:
        self.learning_rate = learning_rate
        self.beta1 = beta1
        self.beta2 = beta2
        self.epsilon = epsilon
        self.t = 0
        self.m: dict[int, float] = {}
        self.v: dict[int, float] = {}

    def apply_gradients(self, pairs: Iterable[tuple[float, Variable]]) -> None:
        self.t += 1
        for grad, var in pairs:
            key = id(var)
            self.m[key] = self.beta1 * self.m.get(key, 0.0) + (1 - self.beta1) * grad
            self.v[key] = self.beta2 * self.v.get(key, 0.0) + (1 - self.beta2) * grad * grad
            m_hat = self.m[key] / (1 - self.beta1 ** self.t)
            v_hat = self.v[key] / (1 - self.beta2 ** self.t)
            var.value -= self.learning_rate * m_hat / (math.sqrt(v_hat) + self.epsilon)


class RMSProp:
    def __init__(self, learning_rate: float = 0.001, rho: float = 0.9, epsilon: float = 1e-7) -> None:
        self.learning_rate = learning_rate
        self.rho = rho
        self.epsilon = epsilon
        self.cache: dict[int, float] = {}

    def apply_gradients(self, pairs: Iterable[tuple[float, Variable]]) -> None:
        for grad, var in pairs:
            key = id(var)
            self.cache[key] = self.rho * self.cache.get(key, 0.0) + (1 - self.rho) * grad * grad
            var.value -= self.learning_rate * grad / (math.sqrt(self.cache[key]) + self.epsilon)


@dataclass
class Dataset:
    rows: list[Any]

    @classmethod
    def from_tensor_slices(cls, rows: Sequence[Any]) -> "Dataset":
        return cls(list(rows))

    def shuffle(self, seed: int = 42) -> "Dataset":
        data = list(self.rows)
        random.Random(seed).shuffle(data)
        return Dataset(data)

    def batch(self, size: int) -> list[list[Any]]:
        return [self.rows[i:i + size] for i in range(0, len(self.rows), size)]

    def map(self, fn: Callable[[Any], Any]) -> "Dataset":
        return Dataset([fn(row) for row in self.rows])

    def take(self, n: int) -> "Dataset":
        return Dataset(self.rows[:n])


@dataclass
class Conv2D:
    filters: int
    kernel_size: int | tuple[int, int]
    activation: str | None = None
    status: str = "architecture_stub"

    def to_config(self) -> dict[str, Any]:
        return self.__dict__


@dataclass
class MaxPool2D:
    pool_size: int | tuple[int, int] = 2
    status: str = "architecture_stub"

    def to_config(self) -> dict[str, Any]:
        return self.__dict__


@dataclass
class Flatten:
    status: str = "architecture_stub"

    def to_config(self) -> dict[str, Any]:
        return self.__dict__


@dataclass
class Dropout:
    rate: float
    status: str = "architecture_stub"

    def to_config(self) -> dict[str, Any]:
        return self.__dict__


@dataclass
class Embedding:
    input_dim: int
    output_dim: int
    status: str = "architecture_stub"

    def to_config(self) -> dict[str, Any]:
        return self.__dict__


@dataclass
class LSTM:
    units: int
    return_sequences: bool = False
    status: str = "architecture_stub"

    def to_config(self) -> dict[str, Any]:
        return self.__dict__


@dataclass
class MultiHeadAttention:
    num_heads: int
    key_dim: int
    status: str = "architecture_stub"

    def to_config(self) -> dict[str, Any]:
        return self.__dict__


def gpu_backends() -> dict[str, Any]:
    return {
        "cuda": {"available": bool(shutil.which("nvidia-smi")), "min_vram_gb": 2},
        "rocm": {"available": bool(shutil.which("rocm-smi")), "min_vram_gb": 2},
        "directml": {"available": False, "min_vram_gb": 2},
        "native_cpu": {"available": True},
    }


def compatibility_bridge() -> dict[str, Any]:
    def can_import(name: str) -> bool:
        try:
            __import__(name)
            return True
        except Exception:
            return False
    return {
        "tensorflow": {"available": can_import("tensorflow"), "role": "optional migration/backend bridge"},
        "torch": {"available": can_import("torch"), "role": "optional research/backend bridge"},
        "onnx": {"available": can_import("onnx"), "role": "model import/export bridge"},
    }


def replacement_matrix() -> dict[str, Any]:
    return {
        "implemented_now": ["Variable", "GradientTape scalar gradients", "Dataset", "Adam", "RMSProp", "save/load architecture specs"],
        "architecture_ready": ["Conv2D", "MaxPool2D", "Flatten", "Dropout", "Embedding", "LSTM", "MultiHeadAttention", "CUDA", "ROCm", "DirectML", "ONNX bridge"],
        "not_claimed_complete_yet": ["full tensor autodiff graph", "production GPU kernels", "distributed training", "full TensorFlow SavedModel compatibility"],
    }


def save_architecture(path: str | Path, layers: Sequence[Any], metadata: dict[str, Any] | None = None) -> str:
    payload = {"format": "agilang-aiflow-architecture", "metadata": metadata or {}, "layers": [layer.to_config() if hasattr(layer, "to_config") else dict(layer) for layer in layers]}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)


def load_architecture(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class layers:
    Conv2D = Conv2D
    MaxPool2D = MaxPool2D
    Flatten = Flatten
    Dropout = Dropout
    Embedding = Embedding
    LSTM = LSTM
    MultiHeadAttention = MultiHeadAttention


class optimizers:
    Adam = Adam
    RMSProp = RMSProp


class data:
    Dataset = Dataset


__all__ = [
    "Variable", "GradientTape", "Adam", "RMSProp", "Dataset",
    "Conv2D", "MaxPool2D", "Flatten", "Dropout", "Embedding", "LSTM", "MultiHeadAttention",
    "gpu_backends", "compatibility_bridge", "replacement_matrix", "save_architecture", "load_architecture",
    "layers", "optimizers", "data",
]
