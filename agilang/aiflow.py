"""AGILANG AIFlow: TensorFlow-style native training layer.

AIFlow is the AGILANG-facing replacement API for common TensorFlow/Keras tasks.
It is intentionally dependency-light and pure Python for portability today, while
keeping a clear API surface for future native/C/WASM/GPU acceleration.

Supported now:
- Tensor wrapper and tensor conversion helpers
- Dense layers
- ReLU, sigmoid, tanh and linear activations
- Sequential model
- SGD optimizer
- MSE and binary cross-entropy losses
- Binary accuracy metric
- fit/predict/evaluate/save/load
- TensorFlow-style aliases: keras.Sequential, layers.Dense, optimizers.SGD

Boundary: this is a TensorFlow-style replacement foundation, not yet a full
replacement for TensorFlow's GPU kernels, autodiff engine, distributed runtime,
CNN/RNN/Transformer layers, TensorBoard, or SavedModel ecosystem.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

Number = int | float


def _as_2d(x: Any) -> list[list[float]]:
    if isinstance(x, Tensor):
        x = x.data
    if not isinstance(x, list):
        return [[float(x)]]
    if not x:
        return []
    if isinstance(x[0], list):
        return [[float(v) for v in row] for row in x]
    return [[float(v) for v in x]]


def _shape(x: Any) -> list[int]:
    data = x.data if isinstance(x, Tensor) else x
    if isinstance(data, list) and data and isinstance(data[0], list):
        return [len(data), len(data[0])]
    if isinstance(data, list):
        return [len(data)]
    return []


@dataclass
class Tensor:
    data: Any
    dtype: str = "float32"
    device: str = "cpu"

    @property
    def shape(self) -> list[int]:
        return _shape(self.data)

    def tolist(self) -> Any:
        return self.data

    def numpy(self) -> Any:
        return self.data


def constant(value: Any, dtype: str = "float32") -> Tensor:
    return Tensor(value, dtype=dtype)


def convert_to_tensor(value: Any, dtype: str = "float32") -> Tensor:
    return Tensor(value, dtype=dtype)


def zeros(shape: Sequence[int]) -> Tensor:
    if len(shape) == 1:
        return Tensor([0.0 for _ in range(shape[0])])
    if len(shape) == 2:
        return Tensor([[0.0 for _ in range(shape[1])] for _ in range(shape[0])])
    raise ValueError("zeros currently supports rank-1 and rank-2 tensors")


def ones(shape: Sequence[int]) -> Tensor:
    if len(shape) == 1:
        return Tensor([1.0 for _ in range(shape[0])])
    if len(shape) == 2:
        return Tensor([[1.0 for _ in range(shape[1])] for _ in range(shape[0])])
    raise ValueError("ones currently supports rank-1 and rank-2 tensors")


def matmul(a: Any, b: Any) -> Tensor:
    left = _as_2d(a)
    right = _as_2d(b)
    if not left or not right:
        return Tensor([])
    if len(left[0]) != len(right):
        raise ValueError(f"matmul shape mismatch: {len(left)}x{len(left[0])} and {len(right)}x{len(right[0])}")
    out = []
    for row in left:
        out_row = []
        for j in range(len(right[0])):
            out_row.append(sum(row[k] * right[k][j] for k in range(len(right))))
        out.append(out_row)
    return Tensor(out)


def relu_value(x: float) -> float:
    return max(0.0, x)


def sigmoid_value(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def tanh_value(x: float) -> float:
    return math.tanh(x)


def activation_fn(name: str | None) -> Callable[[float], float]:
    if name in (None, "linear"):
        return lambda x: x
    if name == "relu":
        return relu_value
    if name == "sigmoid":
        return sigmoid_value
    if name == "tanh":
        return tanh_value
    raise ValueError(f"unsupported activation: {name}")


def activation_grad(name: str | None, activated: float, raw: float) -> float:
    if name in (None, "linear"):
        return 1.0
    if name == "relu":
        return 1.0 if raw > 0 else 0.0
    if name == "sigmoid":
        return activated * (1.0 - activated)
    if name == "tanh":
        return 1.0 - activated * activated
    raise ValueError(f"unsupported activation: {name}")


@dataclass
class Dense:
    units: int
    activation: str | None = None
    input_shape: Sequence[int] | None = None
    seed: int = 42
    weights: list[list[float]] = field(default_factory=list)
    bias: list[float] = field(default_factory=list)
    input_cache: list[float] = field(default_factory=list)
    raw_cache: list[float] = field(default_factory=list)
    output_cache: list[float] = field(default_factory=list)

    def build(self, input_dim: int) -> None:
        if self.weights:
            return
        rnd = random.Random(self.seed + input_dim + self.units)
        scale = math.sqrt(2.0 / max(1, input_dim))
        self.weights = [[rnd.uniform(-scale, scale) for _ in range(self.units)] for _ in range(input_dim)]
        self.bias = [0.0 for _ in range(self.units)]

    def forward_one(self, row: Sequence[Number]) -> list[float]:
        x = [float(v) for v in row]
        self.build(len(x))
        fn = activation_fn(self.activation)
        raw = [sum(x[i] * self.weights[i][j] for i in range(len(x))) + self.bias[j] for j in range(self.units)]
        out = [fn(v) for v in raw]
        self.input_cache = x
        self.raw_cache = raw
        self.output_cache = out
        return out

    def backward_one(self, grad_out: Sequence[Number], lr: float) -> list[float]:
        grad = [float(v) for v in grad_out]
        local = [grad[j] * activation_grad(self.activation, self.output_cache[j], self.raw_cache[j]) for j in range(self.units)]
        grad_input = [0.0 for _ in self.input_cache]
        old_weights = [row[:] for row in self.weights]
        for i, x_i in enumerate(self.input_cache):
            for j in range(self.units):
                grad_input[i] += old_weights[i][j] * local[j]
                self.weights[i][j] -= lr * x_i * local[j]
        for j in range(self.units):
            self.bias[j] -= lr * local[j]
        return grad_input

    def to_config(self) -> dict[str, Any]:
        return {"class": "Dense", "units": self.units, "activation": self.activation, "input_shape": list(self.input_shape) if self.input_shape else None, "weights": self.weights, "bias": self.bias}

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "Dense":
        layer = cls(int(cfg["units"]), cfg.get("activation"), cfg.get("input_shape"))
        layer.weights = [[float(v) for v in row] for row in cfg.get("weights", [])]
        layer.bias = [float(v) for v in cfg.get("bias", [])]
        return layer


@dataclass
class SGD:
    learning_rate: float = 0.01


class Losses:
    @staticmethod
    def mse(y_true: Sequence[Number], y_pred: Sequence[Number]) -> tuple[float, list[float]]:
        n = max(1, len(y_true))
        errors = [float(p) - float(t) for t, p in zip(y_true, y_pred)]
        loss = sum(e * e for e in errors) / n
        grad = [(2.0 / n) * e for e in errors]
        return loss, grad

    @staticmethod
    def binary_crossentropy(y_true: Sequence[Number], y_pred: Sequence[Number]) -> tuple[float, list[float]]:
        eps = 1e-7
        losses = []
        grads = []
        for t, p in zip(y_true, y_pred):
            p = min(max(float(p), eps), 1.0 - eps)
            t = float(t)
            losses.append(-(t * math.log(p) + (1.0 - t) * math.log(1.0 - p)))
            grads.append((p - t) / max(eps, p * (1.0 - p)))
        return sum(losses) / max(1, len(losses)), grads


def _loss(name: str):
    if name in {"mse", "mean_squared_error"}:
        return Losses.mse
    if name in {"binary_crossentropy", "bce"}:
        return Losses.binary_crossentropy
    raise ValueError(f"unsupported loss: {name}")


class Sequential:
    def __init__(self, layers: Sequence[Dense] | None = None) -> None:
        self.layers: list[Dense] = list(layers or [])
        self.optimizer = SGD(0.01)
        self.loss_name = "mse"
        self.metrics: list[str] = []
        self.history: dict[str, list[float]] = {"loss": []}

    def add(self, layer: Dense) -> None:
        self.layers.append(layer)

    def compile(self, optimizer: SGD | str | None = None, loss: str = "mse", metrics: Sequence[str] | None = None) -> None:
        if isinstance(optimizer, SGD):
            self.optimizer = optimizer
        elif isinstance(optimizer, str):
            if optimizer.lower() != "sgd":
                raise ValueError("AIFlow currently supports optimizer='sgd' or SGD(...)")
        self.loss_name = loss
        self.metrics = list(metrics or [])

    def _forward_one(self, row: Sequence[Number]) -> list[float]:
        out = [float(v) for v in row]
        for layer in self.layers:
            out = layer.forward_one(out)
        return out

    def predict(self, x: Sequence[Sequence[Number]]) -> list[list[float]]:
        return [self._forward_one(row) for row in x]

    def fit(self, x: Sequence[Sequence[Number]], y: Sequence[Sequence[Number]], epochs: int = 1, batch_size: int = 1, verbose: int = 0) -> dict[str, list[float]]:
        loss_fn = _loss(self.loss_name)
        lr = self.optimizer.learning_rate
        for epoch in range(epochs):
            total = 0.0
            count = 0
            for row, target in zip(x, y):
                pred = self._forward_one(row)
                loss, grad = loss_fn(target, pred)
                total += loss
                count += 1
                for layer in reversed(self.layers):
                    grad = layer.backward_one(grad, lr)
            epoch_loss = total / max(1, count)
            self.history.setdefault("loss", []).append(epoch_loss)
            if "binary_accuracy" in self.metrics or "accuracy" in self.metrics:
                self.history.setdefault("binary_accuracy", []).append(binary_accuracy(y, self.predict(x)))
            if verbose:
                print({"epoch": epoch + 1, "loss": epoch_loss})
        return self.history

    def evaluate(self, x: Sequence[Sequence[Number]], y: Sequence[Sequence[Number]]) -> dict[str, float]:
        preds = self.predict(x)
        loss_fn = _loss(self.loss_name)
        losses = [loss_fn(t, p)[0] for t, p in zip(y, preds)]
        result = {"loss": sum(losses) / max(1, len(losses))}
        if "binary_accuracy" in self.metrics or "accuracy" in self.metrics:
            result["binary_accuracy"] = binary_accuracy(y, preds)
        return result

    def save(self, path: str | Path) -> str:
        data = {"format": "agilang-aiflow-model", "loss": self.loss_name, "metrics": self.metrics, "optimizer": {"class": "SGD", "learning_rate": self.optimizer.learning_rate}, "layers": [layer.to_config() for layer in self.layers], "history": self.history}
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        return str(path)

    @classmethod
    def load(cls, path: str | Path) -> "Sequential":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        model = cls([Dense.from_config(cfg) for cfg in data.get("layers", [])])
        opt = data.get("optimizer", {})
        model.compile(SGD(float(opt.get("learning_rate", 0.01))), loss=data.get("loss", "mse"), metrics=data.get("metrics", []))
        model.history = data.get("history", {"loss": []})
        return model


def binary_accuracy(y_true: Sequence[Sequence[Number]], y_pred: Sequence[Sequence[Number]]) -> float:
    if not y_true:
        return 0.0
    correct = 0
    for t, p in zip(y_true, y_pred):
        expected = 1 if float(t[0]) >= 0.5 else 0
        got = 1 if float(p[0]) >= 0.5 else 0
        correct += 1 if expected == got else 0
    return correct / len(y_true)


def load_model(path: str | Path) -> Sequential:
    return Sequential.load(path)


class layers:
    Dense = Dense


class optimizers:
    SGD = SGD


class losses:
    mse = "mse"
    mean_squared_error = "mean_squared_error"
    binary_crossentropy = "binary_crossentropy"


class metrics:
    binary_accuracy = "binary_accuracy"
    accuracy = "accuracy"


class keras:
    Sequential = Sequential
    layers = layers
    optimizers = optimizers
    losses = losses
    metrics = metrics
    models = type("models", (), {"load_model": staticmethod(load_model)})


__all__ = [
    "Tensor",
    "Dense",
    "SGD",
    "Sequential",
    "constant",
    "convert_to_tensor",
    "zeros",
    "ones",
    "matmul",
    "binary_accuracy",
    "load_model",
    "keras",
    "layers",
    "optimizers",
    "losses",
    "metrics",
]
