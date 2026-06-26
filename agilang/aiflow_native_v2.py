"""AIFlow Native v2: multi-layer nonlinear native training."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .ndtensor import NDTensor, matmul, mse, ndtensor, sgd_step, variable
from .ndtensor_broadcast import activate, broadcast_add


@dataclass
class NativeDenseV2:
    units: int
    input_dim: int
    activation: str | None = None
    seed: int = 42
    weights: NDTensor = field(init=False)
    bias: NDTensor = field(init=False)

    def __post_init__(self) -> None:
        rnd = random.Random(self.seed + self.units + self.input_dim)
        self.weights = variable([[rnd.uniform(-0.5, 0.5) for _ in range(self.units)] for _ in range(self.input_dim)], name="dense_weights")
        self.bias = variable([0.0 for _ in range(self.units)], name="dense_bias")

    def __call__(self, x: NDTensor) -> NDTensor:
        return activate(broadcast_add(matmul(x, self.weights), self.bias), self.activation)

    def parameters(self) -> list[NDTensor]:
        return [self.weights, self.bias]

    def to_config(self) -> dict[str, Any]:
        return {"class": "NativeDenseV2", "units": self.units, "input_dim": self.input_dim, "activation": self.activation, "weights": self.weights.tolist(), "bias": self.bias.tolist()}

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "NativeDenseV2":
        layer = cls(int(cfg["units"]), int(cfg["input_dim"]), cfg.get("activation"))
        layer.weights = variable(cfg["weights"], name="dense_weights")
        layer.bias = variable(cfg["bias"], name="dense_bias")
        return layer


class NativeSequentialV2:
    def __init__(self, layers: Sequence[NativeDenseV2] | None = None) -> None:
        self.layers = list(layers or [])
        self.history: dict[str, list[float]] = {"loss": []}

    def add(self, layer: NativeDenseV2) -> None:
        self.layers.append(layer)

    def parameters(self) -> list[NDTensor]:
        params: list[NDTensor] = []
        for layer in self.layers:
            params.extend(layer.parameters())
        return params

    def __call__(self, rows: Sequence[Sequence[float]] | Sequence[float]) -> NDTensor:
        if rows and isinstance(rows[0], (int, float)):  # type: ignore[index]
            x = ndtensor([[float(v) for v in rows]])  # type: ignore[arg-type]
        else:
            x = ndtensor([[float(v) for v in row] for row in rows])  # type: ignore[union-attr]
        for layer in self.layers:
            x = layer(x)
        return x

    def predict(self, rows: Sequence[Sequence[float]]) -> list[list[float]]:
        return self(rows).tolist()

    def fit(self, x: Sequence[Sequence[float]], y: Sequence[Sequence[float]], epochs: int = 100, learning_rate: float = 0.01) -> dict[str, list[float]]:
        params = self.parameters()
        target = ndtensor([[float(v) for v in row] for row in y])
        for _ in range(epochs):
            pred = self(x)
            loss = mse(pred, target)
            self.history["loss"].append(loss.item())
            loss.backward()
            sgd_step(params, learning_rate=learning_rate)
        return self.history

    def save(self, path: str | Path) -> str:
        payload = {"format": "agilang-aiflow-native-v2", "layers": [layer.to_config() for layer in self.layers], "history": self.history}
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)

    @classmethod
    def load(cls, path: str | Path) -> "NativeSequentialV2":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        model = cls([NativeDenseV2.from_config(cfg) for cfg in payload.get("layers", [])])
        model.history = payload.get("history", {"loss": []})
        return model


def native_mlp(input_dim: int, hidden: int, output_dim: int, activation: str = "relu") -> NativeSequentialV2:
    return NativeSequentialV2([
        NativeDenseV2(hidden, input_dim, activation=activation),
        NativeDenseV2(output_dim, hidden, activation="linear"),
    ])


def load_native_v2_model(path: str | Path) -> NativeSequentialV2:
    return NativeSequentialV2.load(path)


__all__ = ["NativeDenseV2", "NativeSequentialV2", "native_mlp", "load_native_v2_model"]
