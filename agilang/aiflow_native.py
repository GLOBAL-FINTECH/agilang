"""AIFlow native-autodiff integration layer.

This connects AIFlow model training to the native `NDTensor` autodiff engine.
It is a small but important bridge from architecture descriptors toward real
AGILANG-native training.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .ndtensor import NDTensor, matmul, mse, ndtensor, sgd_step, variable


def _as_column(rows: Sequence[Sequence[float]]) -> list[list[float]]:
    return [[float(v) for v in row] for row in rows]


@dataclass
class NativeDense:
    units: int
    input_dim: int
    seed: int = 42
    weights: NDTensor = field(init=False)
    bias: NDTensor = field(init=False)

    def __post_init__(self) -> None:
        rnd = random.Random(self.seed + self.units + self.input_dim)
        self.weights = variable([[rnd.uniform(-0.5, 0.5) for _ in range(self.units)] for _ in range(self.input_dim)], name="dense_weights")
        self.bias = variable([[0.0 for _ in range(self.units)]], name="dense_bias")

    def __call__(self, x: NDTensor) -> NDTensor:
        # Single-row dense layer for native starter training.
        out = matmul(x, self.weights)
        return out + self.bias

    def parameters(self) -> list[NDTensor]:
        return [self.weights, self.bias]

    def to_config(self) -> dict[str, Any]:
        return {"class": "NativeDense", "units": self.units, "input_dim": self.input_dim, "weights": self.weights.tolist(), "bias": self.bias.tolist()}

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "NativeDense":
        layer = cls(int(cfg["units"]), int(cfg["input_dim"]))
        layer.weights = variable(cfg["weights"], name="dense_weights")
        layer.bias = variable(cfg["bias"], name="dense_bias")
        return layer


class NativeSequential:
    def __init__(self, layers: Sequence[NativeDense] | None = None) -> None:
        self.layers = list(layers or [])
        self.history: dict[str, list[float]] = {"loss": []}

    def add(self, layer: NativeDense) -> None:
        self.layers.append(layer)

    def parameters(self) -> list[NDTensor]:
        params: list[NDTensor] = []
        for layer in self.layers:
            params.extend(layer.parameters())
        return params

    def __call__(self, row: Sequence[float]) -> NDTensor:
        x = ndtensor([list(float(v) for v in row)])
        for layer in self.layers:
            x = layer(x)
        return x

    def predict(self, rows: Sequence[Sequence[float]]) -> list[list[float]]:
        return [self(row).tolist()[0] for row in rows]

    def fit(self, x: Sequence[Sequence[float]], y: Sequence[Sequence[float]], epochs: int = 50, learning_rate: float = 0.01) -> dict[str, list[float]]:
        params = self.parameters()
        for _ in range(epochs):
            total = 0.0
            for row, target in zip(x, y):
                pred = self(row)
                loss = mse(pred, ndtensor([list(float(v) for v in target)]))
                total += loss.item()
                loss.backward()
                sgd_step(params, learning_rate=learning_rate)
            self.history["loss"].append(total / max(1, len(x)))
        return self.history

    def save(self, path: str | Path) -> str:
        payload = {"format": "agilang-aiflow-native", "layers": [layer.to_config() for layer in self.layers], "history": self.history}
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)

    @classmethod
    def load(cls, path: str | Path) -> "NativeSequential":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        model = cls([NativeDense.from_config(cfg) for cfg in payload.get("layers", [])])
        model.history = payload.get("history", {"loss": []})
        return model


def native_linear_model(input_dim: int = 1, output_dim: int = 1, seed: int = 42) -> NativeSequential:
    return NativeSequential([NativeDense(output_dim, input_dim, seed=seed)])


def load_native_model(path: str | Path) -> NativeSequential:
    return NativeSequential.load(path)


__all__ = ["NativeDense", "NativeSequential", "native_linear_model", "load_native_model"]
