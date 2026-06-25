"""AGILANG AI, tensor, ML, and training toolkit.

This module provides a dependency-light native baseline for AGILANG AI work:
- tensors and matrix operations
- CPU/RAM/GPU runtime detection and backend selection
- data summaries, scaling and train/test splitting
- classical ML helpers
- a small neural-network trainer for demos and starter models
- model save/load utilities
- audio/video pipeline descriptors for future heavy backends

It is designed as the AGILANG-facing API. Python/TensorFlow/PyTorch backends can
be used as optional accelerators while AGILANG native tensors mature.
"""
from __future__ import annotations

import json
import math
import os
import platform
import random
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

Number = int | float


def _is_matrix(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and isinstance(value[0], list)


def _shape(data: Any) -> list[int]:
    if isinstance(data, Tensor):
        return list(data.shape)
    if _is_matrix(data):
        return [len(data), len(data[0]) if data else 0]
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

    def to(self, device: str) -> "Tensor":
        return Tensor(self.data, dtype=self.dtype, device=device)

    def map(self, fn) -> "Tensor":
        if _is_matrix(self.data):
            return Tensor([[fn(float(v)) for v in row] for row in self.data], self.dtype, self.device)
        return Tensor([fn(float(v)) for v in self.data], self.dtype, self.device)


def tensor(data: Any, dtype: str = "float32", device: str = "auto") -> Tensor:
    if device == "auto":
        device = ai_select_backend()["device"]
    return Tensor(data, dtype=dtype, device=device)


def tensor_shape(value: Any) -> list[int]:
    return _shape(value)


def tensor_dot(a: Sequence[Number], b: Sequence[Number]) -> float:
    return float(sum(float(x) * float(y) for x, y in zip(a, b)))


def tensor_matmul(a: Tensor | list[list[Number]], b: Tensor | list[list[Number]]) -> Tensor:
    left = a.data if isinstance(a, Tensor) else a
    right = b.data if isinstance(b, Tensor) else b
    if not _is_matrix(left) or not _is_matrix(right):
        raise ValueError("tensor_matmul expects two matrix-shaped tensors")
    rows = len(left)
    inner = len(left[0])
    if len(right) != inner:
        raise ValueError(f"shape mismatch: {len(left)}x{inner} cannot multiply {len(right)}x{len(right[0]) if right else 0}")
    cols = len(right[0])
    out = []
    for i in range(rows):
        row = []
        for j in range(cols):
            row.append(sum(float(left[i][k]) * float(right[k][j]) for k in range(inner)))
        out.append(row)
    return Tensor(out, device=a.device if isinstance(a, Tensor) else "cpu")


def tensor_add(a: Tensor, b: Tensor | Number) -> Tensor:
    if isinstance(b, Tensor):
        if _is_matrix(a.data):
            return Tensor([[float(x) + float(y) for x, y in zip(ar, br)] for ar, br in zip(a.data, b.data)], a.dtype, a.device)
        return Tensor([float(x) + float(y) for x, y in zip(a.data, b.data)], a.dtype, a.device)
    if _is_matrix(a.data):
        return Tensor([[float(x) + float(b) for x in row] for row in a.data], a.dtype, a.device)
    return Tensor([float(x) + float(b) for x in a.data], a.dtype, a.device)


def tensor_relu(x: Tensor) -> Tensor:
    return x.map(lambda v: max(0.0, v))


def tensor_sigmoid(x: Tensor) -> Tensor:
    return x.map(lambda v: 1.0 / (1.0 + math.exp(-v)))


def tensor_softmax(values: Tensor | Sequence[Number]) -> list[float]:
    raw = values.data if isinstance(values, Tensor) else values
    vals = [float(v) for v in raw]
    m = max(vals)
    exps = [math.exp(v - m) for v in vals]
    total = sum(exps) or 1.0
    return [v / total for v in exps]


def tensor_mean(values: Tensor | Sequence[Number]) -> float:
    raw = values.data if isinstance(values, Tensor) else values
    vals = [float(v) for v in raw]
    return sum(vals) / len(vals) if vals else 0.0


def ai_runtime_info() -> dict[str, Any]:
    total_ram_gb = None
    try:
        import psutil  # type: ignore
        total_ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 2)
    except Exception:
        total_ram_gb = None
    gpus: list[dict[str, Any]] = []
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        gpus.append({"backend": "cuda", "available": True, "min_supported_vram_gb": 2})
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "ram_gb": total_ram_gb,
        "gpu": {"available": bool(gpus), "devices": gpus, "policy": "GPU acceleration is enabled when a compatible GPU has 2GB+ VRAM; otherwise CPU fallback is used."},
        "backends": {"native": True, "tensorflow": _can_import("tensorflow"), "torch": _can_import("torch"), "numpy": _can_import("numpy")},
    }


def _can_import(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def ai_select_backend(prefer: str = "auto", min_gpu_gb: int = 2) -> dict[str, Any]:
    info = ai_runtime_info()
    if prefer in {"tensorflow", "tf"} and info["backends"]["tensorflow"]:
        return {"backend": "tensorflow", "device": "gpu" if info["gpu"]["available"] else "cpu", "ok": True}
    if prefer in {"torch", "pytorch"} and info["backends"]["torch"]:
        return {"backend": "torch", "device": "gpu" if info["gpu"]["available"] else "cpu", "ok": True}
    if info["gpu"]["available"] and (info["backends"]["tensorflow"] or info["backends"]["torch"]):
        return {"backend": "tensorflow" if info["backends"]["tensorflow"] else "torch", "device": "gpu", "ok": True, "min_gpu_gb": min_gpu_gb}
    return {"backend": "agilang-native", "device": "cpu", "ok": True, "reason": "CPU fallback selected"}


def dataset_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    cols = sorted({k for row in rows for k in row.keys()})
    numeric: dict[str, Any] = {}
    missing: dict[str, int] = {c: 0 for c in cols}
    for col in cols:
        vals = []
        for row in rows:
            value = row.get(col)
            if value is None or value == "":
                missing[col] += 1
                continue
            if isinstance(value, (int, float)):
                vals.append(float(value))
        if vals:
            numeric[col] = {"count": len(vals), "min": min(vals), "max": max(vals), "mean": sum(vals) / len(vals)}
    return {"rows": len(rows), "columns": cols, "numeric": numeric, "missing": missing}


def train_test_split(rows: Sequence[Any], test_ratio: float = 0.2, seed: int = 42) -> dict[str, list[Any]]:
    data = list(rows)
    rnd = random.Random(seed)
    rnd.shuffle(data)
    cut = max(1, int(len(data) * (1 - test_ratio))) if data else 0
    return {"train": data[:cut], "test": data[cut:]}


def minmax_scale(rows: Sequence[dict[str, Any]], columns: Sequence[str] | None = None) -> list[dict[str, Any]]:
    columns = list(columns or sorted({k for row in rows for k, v in row.items() if isinstance(v, (int, float))}))
    mins = {c: min(float(r[c]) for r in rows if isinstance(r.get(c), (int, float))) for c in columns}
    maxs = {c: max(float(r[c]) for r in rows if isinstance(r.get(c), (int, float))) for c in columns}
    out = []
    for row in rows:
        item = dict(row)
        for c in columns:
            span = maxs[c] - mins[c]
            item[c] = 0.0 if span == 0 else (float(row[c]) - mins[c]) / span
        out.append(item)
    return out


def linear_regression(rows: Sequence[dict[str, Any]], features: Sequence[str], target: str) -> dict[str, Any]:
    if len(features) != 1:
        raise ValueError("native linear_regression currently supports one feature; use TensorFlow/PyTorch bridge for multi-feature training")
    f = features[0]
    xs = [float(r[f]) for r in rows]
    ys = [float(r[target]) for r in rows]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    denom = sum((x - mx) ** 2 for x in xs) or 1.0
    weight = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    intercept = my - weight * mx
    preds = [intercept + weight * x for x in xs]
    ss_res = sum((y - p) ** 2 for y, p in zip(ys, preds))
    ss_tot = sum((y - my) ** 2 for y in ys) or 1.0
    return {"type": "linear_regression", "features": list(features), "target": target, "intercept": intercept, "weights": {f: weight}, "r2": 1 - ss_res / ss_tot}


def predict_linear(model: dict[str, Any], row: dict[str, Any]) -> float:
    result = float(model.get("intercept", 0.0))
    for feature, weight in model.get("weights", {}).items():
        result += float(weight) * float(row[feature])
    return result


def logistic_regression(rows: Sequence[dict[str, Any]], features: Sequence[str], target: str, epochs: int = 200, lr: float = 0.1) -> dict[str, Any]:
    weights = {f: 0.0 for f in features}
    bias = 0.0
    for _ in range(epochs):
        for row in rows:
            z = bias + sum(weights[f] * float(row[f]) for f in features)
            pred = 1.0 / (1.0 + math.exp(-z))
            err = pred - float(row[target])
            bias -= lr * err
            for f in features:
                weights[f] -= lr * err * float(row[f])
    return {"type": "logistic_regression", "features": list(features), "target": target, "weights": weights, "bias": bias}


def predict_logistic(model: dict[str, Any], row: dict[str, Any]) -> int:
    z = float(model.get("bias", 0.0)) + sum(float(w) * float(row[f]) for f, w in model.get("weights", {}).items())
    return 1 if 1.0 / (1.0 + math.exp(-z)) >= 0.5 else 0


def kmeans(points: Sequence[Sequence[Number]], k: int = 2, iterations: int = 20, seed: int = 42) -> dict[str, Any]:
    pts = [[float(v) for v in p] for p in points]
    rnd = random.Random(seed)
    centers = [list(p) for p in rnd.sample(pts, k)]
    labels = [0] * len(pts)
    for _ in range(iterations):
        for i, p in enumerate(pts):
            labels[i] = min(range(k), key=lambda c: sum((p[j] - centers[c][j]) ** 2 for j in range(len(p))))
        for c in range(k):
            group = [p for p, label in zip(pts, labels) if label == c]
            if group:
                centers[c] = [sum(p[j] for p in group) / len(group) for j in range(len(group[0]))]
    return {"type": "kmeans", "k": k, "centers": centers, "labels": labels}


def neural_network_train(x: Sequence[Sequence[Number]], y: Sequence[Sequence[Number]], hidden: int = 4, epochs: int = 200, lr: float = 0.05, seed: int = 42) -> dict[str, Any]:
    rnd = random.Random(seed)
    input_size = len(x[0])
    output_size = len(y[0])
    w1 = [[rnd.uniform(-0.5, 0.5) for _ in range(hidden)] for _ in range(input_size)]
    b1 = [0.0] * hidden
    w2 = [[rnd.uniform(-0.5, 0.5) for _ in range(output_size)] for _ in range(hidden)]
    b2 = [0.0] * output_size
    losses = []
    for _ in range(epochs):
        total = 0.0
        for xi, yi in zip(x, y):
            h_raw = [sum(float(xi[i]) * w1[i][j] for i in range(input_size)) + b1[j] for j in range(hidden)]
            h = [max(0.0, v) for v in h_raw]
            out = [sum(h[j] * w2[j][o] for j in range(hidden)) + b2[o] for o in range(output_size)]
            errs = [out[o] - float(yi[o]) for o in range(output_size)]
            total += sum(e * e for e in errs) / output_size
            for j in range(hidden):
                for o in range(output_size):
                    w2[j][o] -= lr * errs[o] * h[j]
            for o in range(output_size):
                b2[o] -= lr * errs[o]
            for j in range(hidden):
                grad_h = sum(errs[o] * w2[j][o] for o in range(output_size)) * (1.0 if h_raw[j] > 0 else 0.0)
                for i in range(input_size):
                    w1[i][j] -= lr * grad_h * float(xi[i])
                b1[j] -= lr * grad_h
        losses.append(total / len(x))
    return {"type": "neural_network", "input_size": input_size, "hidden": hidden, "output_size": output_size, "w1": w1, "b1": b1, "w2": w2, "b2": b2, "loss": losses[-1], "losses": losses[-10:]}


def neural_network_predict(model: dict[str, Any], x: Sequence[Number]) -> list[float]:
    w1, b1, w2, b2 = model["w1"], model["b1"], model["w2"], model["b2"]
    hidden = len(b1)
    output_size = len(b2)
    h = [max(0.0, sum(float(x[i]) * w1[i][j] for i in range(len(x))) + b1[j]) for j in range(hidden)]
    return [sum(h[j] * w2[j][o] for j in range(hidden)) + b2[o] for o in range(output_size)]


def model_save(path: str | Path, model: dict[str, Any]) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(model, indent=2), encoding="utf-8")
    return str(path)


def model_load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def chart_spec(kind: str, data: Any, title: str = "AGILANG Chart") -> dict[str, Any]:
    return {"type": kind, "title": title, "data": data, "renderer": "ags"}


def audio_pipeline(task: str = "speech_to_text", backend: str = "auto") -> dict[str, Any]:
    return {"task": task, "backend": ai_select_backend(backend), "steps": ["load_audio", "resample", "extract_features", "train_or_infer", "export_model"], "supported": ["speech_to_text", "text_to_speech", "voice_embedding", "audio_classification"]}


def video_pipeline(task: str = "classification", backend: str = "auto") -> dict[str, Any]:
    return {"task": task, "backend": ai_select_backend(backend), "steps": ["load_video", "extract_frames", "resize", "batch_tensor", "train_or_infer", "export_model"], "supported": ["classification", "object_detection", "tracking", "scene_analysis"]}


def tensorflow_bridge_status() -> dict[str, Any]:
    return {"available": _can_import("tensorflow"), "backend": "tensorflow", "note": "Use this bridge for large CNN/RNN/Transformer training until AGILANG native GPU backend matures."}


def pytorch_bridge_status() -> dict[str, Any]:
    return {"available": _can_import("torch"), "backend": "torch", "note": "Use this bridge for advanced research models and GPU training."}


__all__ = [name for name in globals() if not name.startswith("_")]
