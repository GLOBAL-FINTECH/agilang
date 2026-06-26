"""AGILANG machine-learning, data-analysis, tensor and AI runtime helpers.

The module is dependency-free by default so AGILANG projects work immediately on
small servers and student machines. It is intentionally compatible with the
Python-hosted runtime and exposes primitives that AGILANG code can call directly.

Design goals:
- data loading/cleaning/splitting/scaling
- classical ML algorithms
- small neural-network training for education and lightweight production tasks
- tensor/scientific-computing operations
- visualization specs that can be rendered by web frontends
- model persistence
- RAM/GPU capability reporting

For heavy production AI workloads, generated AGILANG projects can later bridge to
NumPy, pandas, PyTorch, TensorFlow, ONNX Runtime, CUDA/ROCm and vendor drivers
through the existing Python interop layer while keeping AGILANG source as the
application language.
"""
from __future__ import annotations

import csv
import json
import math
import os
import platform
import random
import shutil
import subprocess
from pathlib import Path
from typing import Any, Sequence

Number = int | float


# ---------------------------------------------------------------------------
# Data processing
# ---------------------------------------------------------------------------

def ml_read_csv(path: str | Path, *, numeric: bool = True) -> list[dict[str, Any]]:
    """Read a CSV file into a list of dictionaries."""
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append({k: _coerce_number(v) if numeric else v for k, v in row.items()})
    return rows


def ml_write_csv(path: str | Path, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Write row dictionaries to CSV."""
    data = list(rows)
    columns = sorted({key for row in data for key in row.keys()})
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)
    return {"ok": True, "path": str(path), "rows": len(data), "columns": columns}


def ml_dataset_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Return row count, columns, missing counts and numeric statistics."""
    data = list(rows)
    columns = sorted({key for row in data for key in row.keys()})
    numeric: dict[str, list[float]] = {col: [] for col in columns}
    missing = {col: 0 for col in columns}
    for row in data:
        for col in columns:
            value = row.get(col)
            if value in (None, ""):
                missing[col] += 1
                continue
            try:
                numeric[col].append(float(value))
            except (TypeError, ValueError):
                pass
    stats: dict[str, dict[str, float]] = {}
    for col, values in numeric.items():
        if values:
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            stats[col] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": mean,
                "variance": variance,
                "std": math.sqrt(variance),
            }
    return {"rows": len(data), "columns": columns, "missing": missing, "numeric": stats}


def ml_missing_values(rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    """Count missing values per column."""
    return dict(ml_dataset_summary(rows)["missing"])


def ml_fill_missing(rows: Sequence[dict[str, Any]], strategy: str = "mean", fill_value: Any = 0) -> list[dict[str, Any]]:
    """Fill missing values using mean, median, mode or a constant value."""
    data = [dict(row) for row in rows]
    columns = sorted({key for row in data for key in row.keys()})
    replacements: dict[str, Any] = {}
    for col in columns:
        values = [row.get(col) for row in data if row.get(col) not in (None, "")]
        nums: list[float] = []
        for value in values:
            try:
                nums.append(float(value))
            except (TypeError, ValueError):
                pass
        if strategy == "mean" and nums:
            replacements[col] = sum(nums) / len(nums)
        elif strategy == "median" and nums:
            ordered = sorted(nums)
            mid = len(ordered) // 2
            replacements[col] = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
        elif strategy == "mode" and values:
            counts: dict[Any, int] = {}
            for value in values:
                counts[value] = counts.get(value, 0) + 1
            replacements[col] = max(counts, key=counts.get)
        else:
            replacements[col] = fill_value
    for row in data:
        for col in columns:
            if row.get(col) in (None, ""):
                row[col] = replacements[col]
    return data


def ml_train_test_split(rows: Sequence[dict[str, Any]], test_ratio: float = 0.2, *, shuffle: bool = False, seed: int = 42) -> dict[str, Any]:
    """Split rows into train/test sets."""
    data = list(rows)
    if shuffle:
        rnd = random.Random(seed)
        rnd.shuffle(data)
    if not data:
        return {"train": [], "test": []}
    ratio = min(0.9, max(0.0, float(test_ratio)))
    test_size = max(1, int(round(len(data) * ratio))) if ratio > 0 else 0
    split = max(0, len(data) - test_size)
    return {"train": data[:split], "test": data[split:]}


def ml_minmax_scale(rows: Sequence[dict[str, Any]], columns: Sequence[str]) -> list[dict[str, Any]]:
    """Return rows with selected numeric columns scaled into [0, 1]."""
    data = [dict(row) for row in rows]
    for col in columns:
        values = [float(row.get(col, 0) or 0) for row in data]
        low, high = (min(values), max(values)) if values else (0.0, 0.0)
        span = high - low
        for row in data:
            row[col] = 0.0 if span == 0 else (float(row.get(col, 0) or 0) - low) / span
    return data


def ml_standard_scale(rows: Sequence[dict[str, Any]], columns: Sequence[str]) -> list[dict[str, Any]]:
    """Return rows with selected columns standardized to mean 0, std 1."""
    data = [dict(row) for row in rows]
    for col in columns:
        values = [float(row.get(col, 0) or 0) for row in data]
        mean = sum(values) / len(values) if values else 0.0
        variance = sum((v - mean) ** 2 for v in values) / len(values) if values else 0.0
        std = math.sqrt(variance) or 1.0
        for row in data:
            row[col] = (float(row.get(col, 0) or 0) - mean) / std
    return data


# ---------------------------------------------------------------------------
# Tensor / scientific computing
# ---------------------------------------------------------------------------

def tensor_shape(value: Any) -> list[int]:
    """Return nested-list tensor shape."""
    shape: list[int] = []
    cursor = value
    while isinstance(cursor, list):
        shape.append(len(cursor))
        cursor = cursor[0] if cursor else []
    return shape


def tensor_zeros(shape: Sequence[int]) -> Any:
    """Create a nested list tensor filled with zeros."""
    dims = list(shape)
    if not dims:
        return 0.0
    return [tensor_zeros(dims[1:]) for _ in range(int(dims[0]))]


def tensor_random(shape: Sequence[int], seed: int = 42, low: float = -0.1, high: float = 0.1) -> Any:
    """Create a deterministic random tensor."""
    rnd = random.Random(seed)
    def build(dims: list[int]) -> Any:
        if not dims:
            return rnd.uniform(low, high)
        return [build(dims[1:]) for _ in range(int(dims[0]))]
    return build(list(shape))


def tensor_transpose(matrix: Sequence[Sequence[Number]]) -> list[list[float]]:
    return [list(map(float, col)) for col in zip(*matrix)]


def tensor_dot(a: Sequence[Number], b: Sequence[Number]) -> float:
    return sum(float(x) * float(y) for x, y in zip(a, b))


def tensor_matmul(a: Sequence[Sequence[Number]], b: Sequence[Sequence[Number]]) -> list[list[float]]:
    b_t = tensor_transpose(b)
    return [[tensor_dot(row, col) for col in b_t] for row in a]


def tensor_add(a: Any, b: Any) -> Any:
    return _elementwise(a, b, lambda x, y: x + y)


def tensor_sub(a: Any, b: Any) -> Any:
    return _elementwise(a, b, lambda x, y: x - y)


def tensor_mul(a: Any, b: Any) -> Any:
    return _elementwise(a, b, lambda x, y: x * y)


def tensor_mean(values: Sequence[Number]) -> float:
    data = [float(v) for v in values]
    return sum(data) / len(data) if data else 0.0


def tensor_variance(values: Sequence[Number]) -> float:
    data = [float(v) for v in values]
    mean = tensor_mean(data)
    return sum((v - mean) ** 2 for v in data) / len(data) if data else 0.0


def tensor_relu(values: Any) -> Any:
    return _map_nested(values, lambda x: max(0.0, x))


def tensor_sigmoid(values: Any) -> Any:
    return _map_nested(values, lambda x: 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, x)))))


def tensor_softmax(values: Sequence[Number]) -> list[float]:
    data = [float(v) for v in values]
    if not data:
        return []
    top = max(data)
    exps = [math.exp(v - top) for v in data]
    total = sum(exps) or 1.0
    return [v / total for v in exps]


def _map_nested(value: Any, fn) -> Any:
    if isinstance(value, list):
        return [_map_nested(item, fn) for item in value]
    return fn(float(value))


def _elementwise(a: Any, b: Any, fn) -> Any:
    if isinstance(a, list) and isinstance(b, list):
        return [_elementwise(x, y, fn) for x, y in zip(a, b)]
    if isinstance(a, list):
        return [_elementwise(x, b, fn) for x in a]
    if isinstance(b, list):
        return [_elementwise(a, y, fn) for y in b]
    return fn(float(a), float(b))


# ---------------------------------------------------------------------------
# Classical ML
# ---------------------------------------------------------------------------

def _features(row: dict[str, Any], feature_columns: Sequence[str]) -> list[float]:
    return [float(row.get(col, 0) or 0) for col in feature_columns]


def ml_linear_regression(rows: Sequence[dict[str, Any]], target: str, features: Sequence[str]) -> dict[str, Any]:
    """Train an ordinary-least-squares linear regression model."""
    data = list(rows)
    feature_columns = list(features)
    if not data:
        return {"type": "linear_regression", "features": feature_columns, "target": target, "intercept": 0.0, "weights": {col: 0.0 for col in feature_columns}, "r2": 0.0}
    if len(feature_columns) == 1:
        col = feature_columns[0]
        xs = [float(row.get(col, 0) or 0) for row in data]
        ys = [float(row.get(target, 0) or 0) for row in data]
        x_mean = sum(xs) / len(xs)
        y_mean = sum(ys) / len(ys)
        denom = sum((x - x_mean) ** 2 for x in xs)
        slope = 0.0 if denom == 0 else sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denom
        intercept = y_mean - slope * x_mean
        preds = [intercept + slope * x for x in xs]
        return {"type": "linear_regression", "features": feature_columns, "target": target, "intercept": intercept, "weights": {col: slope}, "r2": _r2(ys, preds)}
    weights = [0.0 for _ in feature_columns]
    intercept = 0.0
    rate = 0.001
    for _ in range(2000):
        grad_w = [0.0 for _ in feature_columns]
        grad_b = 0.0
        for row in data:
            xs = _features(row, feature_columns)
            y = float(row.get(target, 0) or 0)
            pred = intercept + sum(w * x for w, x in zip(weights, xs))
            error = pred - y
            grad_b += error
            for i, x in enumerate(xs):
                grad_w[i] += error * x
        n = max(1, len(data))
        intercept -= rate * grad_b / n
        for i in range(len(weights)):
            weights[i] -= rate * grad_w[i] / n
    preds = [intercept + sum(w * x for w, x in zip(weights, _features(row, feature_columns))) for row in data]
    ys = [float(row.get(target, 0) or 0) for row in data]
    return {"type": "linear_regression", "features": feature_columns, "target": target, "intercept": intercept, "weights": dict(zip(feature_columns, weights)), "r2": _r2(ys, preds)}


def ml_predict_linear(model: dict[str, Any], row: dict[str, Any]) -> float:
    total = float(model.get("intercept", 0.0) or 0.0)
    for col, weight in dict(model.get("weights", {})).items():
        total += float(weight or 0.0) * float(row.get(col, 0) or 0)
    return total


def ml_logistic_regression(rows: Sequence[dict[str, Any]], target: str, features: Sequence[str], *, epochs: int = 1200, learning_rate: float = 0.1) -> dict[str, Any]:
    """Train a binary logistic-regression classifier."""
    data = list(rows)
    cols = list(features)
    weights = [0.0 for _ in cols]
    bias = 0.0
    for _ in range(int(epochs)):
        grad_w = [0.0 for _ in cols]
        grad_b = 0.0
        for row in data:
            xs = _features(row, cols)
            y = 1.0 if float(row.get(target, 0) or 0) >= 1 else 0.0
            z = bias + sum(w * x for w, x in zip(weights, xs))
            pred = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))
            error = pred - y
            grad_b += error
            for i, x in enumerate(xs):
                grad_w[i] += error * x
        n = max(1, len(data))
        bias -= learning_rate * grad_b / n
        for i in range(len(weights)):
            weights[i] -= learning_rate * grad_w[i] / n
    preds = [ml_predict_logistic({"bias": bias, "weights": dict(zip(cols, weights))}, row)["class"] for row in data]
    truth = [1 if float(row.get(target, 0) or 0) >= 1 else 0 for row in data]
    return {"type": "logistic_regression", "features": cols, "target": target, "bias": bias, "weights": dict(zip(cols, weights)), "accuracy": ml_accuracy(truth, preds)}


def ml_predict_logistic(model: dict[str, Any], row: dict[str, Any], threshold: float = 0.5) -> dict[str, Any]:
    z = float(model.get("bias", 0.0) or 0.0)
    for col, weight in dict(model.get("weights", {})).items():
        z += float(weight or 0.0) * float(row.get(col, 0) or 0)
    prob = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))
    return {"probability": prob, "class": 1 if prob >= threshold else 0}


def ml_kmeans(rows: Sequence[dict[str, Any]], features: Sequence[str], k: int = 2, *, iterations: int = 30) -> dict[str, Any]:
    """Run small deterministic K-Means clustering."""
    data = list(rows)
    cols = list(features)
    points = [_features(row, cols) for row in data]
    if not points:
        return {"type": "kmeans", "k": k, "centroids": [], "assignments": []}
    k = max(1, min(int(k), len(points)))
    centroids = [points[i][:] for i in range(k)]
    assignments = [0 for _ in points]
    for _ in range(iterations):
        assignments = [_nearest(point, centroids) for point in points]
        for c in range(k):
            members = [p for p, a in zip(points, assignments) if a == c]
            if members:
                centroids[c] = [sum(p[i] for p in members) / len(members) for i in range(len(cols))]
    return {"type": "kmeans", "features": cols, "k": k, "centroids": centroids, "assignments": assignments}


def ml_decision_stump(rows: Sequence[dict[str, Any]], target: str, features: Sequence[str]) -> dict[str, Any]:
    """Train a one-level decision tree classifier."""
    data = list(rows)
    best = {"feature": None, "threshold": 0.0, "score": -1.0, "left": 0, "right": 1}
    for col in features:
        values = sorted({float(row.get(col, 0) or 0) for row in data})
        for threshold in values:
            left_labels = [int(row.get(target, 0) or 0) for row in data if float(row.get(col, 0) or 0) <= threshold]
            right_labels = [int(row.get(target, 0) or 0) for row in data if float(row.get(col, 0) or 0) > threshold]
            left = _majority(left_labels)
            right = _majority(right_labels)
            preds = [left if float(row.get(col, 0) or 0) <= threshold else right for row in data]
            truth = [int(row.get(target, 0) or 0) for row in data]
            score = ml_accuracy(truth, preds)
            if score > best["score"]:
                best = {"feature": col, "threshold": threshold, "score": score, "left": left, "right": right}
    return {"type": "decision_stump", "target": target, **best}


def ml_predict_tree(model: dict[str, Any], row: dict[str, Any]) -> Any:
    feature = model.get("feature")
    if feature is None:
        return None
    return model.get("left") if float(row.get(str(feature), 0) or 0) <= float(model.get("threshold", 0)) else model.get("right")


def ml_accuracy(y_true: Sequence[Any], y_pred: Sequence[Any]) -> float:
    truth = list(y_true)
    preds = list(y_pred)
    if not truth:
        return 0.0
    return sum(1 for a, b in zip(truth, preds) if a == b) / len(truth)


def ml_confusion_matrix(y_true: Sequence[Any], y_pred: Sequence[Any]) -> dict[str, Any]:
    labels = sorted({*list(y_true), *list(y_pred)})
    matrix = {str(a): {str(b): 0 for b in labels} for a in labels}
    for actual, pred in zip(y_true, y_pred):
        matrix[str(actual)][str(pred)] += 1
    return {"labels": labels, "matrix": matrix}


# ---------------------------------------------------------------------------
# Lightweight neural network / deep learning starter
# ---------------------------------------------------------------------------

def ml_neural_network_train(rows: Sequence[dict[str, Any]], target: str, features: Sequence[str], *, hidden: int = 4, epochs: int = 1000, learning_rate: float = 0.1, seed: int = 42) -> dict[str, Any]:
    """Train a small one-hidden-layer neural network for binary classification.

    This is dependency-free and intended for AGILANG education, demos, tiny
    models and runtime validation. Large deep-learning workloads should use the
    GPU bridge to PyTorch/TensorFlow/ONNX through interop.
    """
    rnd = random.Random(seed)
    data = list(rows)
    cols = list(features)
    hidden = max(1, int(hidden))
    w1 = [[rnd.uniform(-0.5, 0.5) for _ in cols] for _ in range(hidden)]
    b1 = [0.0 for _ in range(hidden)]
    w2 = [rnd.uniform(-0.5, 0.5) for _ in range(hidden)]
    b2 = 0.0
    losses: list[float] = []
    for epoch in range(int(epochs)):
        total_loss = 0.0
        for row in data:
            x = _features(row, cols)
            y = 1.0 if float(row.get(target, 0) or 0) >= 1 else 0.0
            h_raw = [b1[j] + tensor_dot(w1[j], x) for j in range(hidden)]
            h = [1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, v)))) for v in h_raw]
            z = b2 + tensor_dot(w2, h)
            pred = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))
            error = pred - y
            total_loss += -(y * math.log(max(pred, 1e-9)) + (1 - y) * math.log(max(1 - pred, 1e-9)))
            for j in range(hidden):
                old_w2 = w2[j]
                w2[j] -= learning_rate * error * h[j]
                grad_h = error * old_w2 * h[j] * (1 - h[j])
                for i in range(len(cols)):
                    w1[j][i] -= learning_rate * grad_h * x[i]
                b1[j] -= learning_rate * grad_h
            b2 -= learning_rate * error
        if epoch % max(1, int(epochs) // 10) == 0 or epoch == int(epochs) - 1:
            losses.append(total_loss / max(1, len(data)))
    model = {"type": "neural_network_binary", "features": cols, "target": target, "hidden": hidden, "w1": w1, "b1": b1, "w2": w2, "b2": b2, "loss": losses}
    preds = [ml_neural_network_predict(model, row)["class"] for row in data]
    truth = [1 if float(row.get(target, 0) or 0) >= 1 else 0 for row in data]
    model["accuracy"] = ml_accuracy(truth, preds)
    return model


def ml_neural_network_predict(model: dict[str, Any], row: dict[str, Any], threshold: float = 0.5) -> dict[str, Any]:
    cols = list(model.get("features", []))
    x = _features(row, cols)
    w1 = model.get("w1", [])
    b1 = model.get("b1", [])
    w2 = model.get("w2", [])
    h = []
    for j, weights in enumerate(w1):
        z = float(b1[j]) + tensor_dot(weights, x)
        h.append(1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z)))))
    z2 = float(model.get("b2", 0.0)) + tensor_dot(w2, h)
    prob = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z2))))
    return {"probability": prob, "class": 1 if prob >= threshold else 0}


# ---------------------------------------------------------------------------
# Visualization, model persistence, runtime resources
# ---------------------------------------------------------------------------

def ml_chart_spec(rows: Sequence[dict[str, Any]], chart: str, x: str, y: str | None = None, title: str = "AGILANG Chart") -> dict[str, Any]:
    """Return a frontend-neutral chart specification for AGS/web rendering."""
    return {"type": "chart", "chart": chart, "title": title, "x": x, "y": y, "data": list(rows)}


def ml_save_model(model: dict[str, Any], path: str | Path) -> dict[str, Any]:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(model, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(path), "type": model.get("type")}


def ml_load_model(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ai_runtime_info() -> dict[str, Any]:
    """Report CPU/RAM/GPU capability using stdlib and optional system tools."""
    info: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "ram": _ram_info(),
        "gpu": _gpu_info(),
        "policy": {
            "minimum_gpu_memory_recommended_gb": 2,
            "works_without_gpu": True,
            "gpu_backend_strategy": ["CUDA via PyTorch/TensorFlow interop", "ROCm where supported", "CPU fallback"],
        },
    }
    return info


def _ram_info() -> dict[str, Any]:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        total = int(pages) * int(page_size)
        return {"total_bytes": total, "total_gb": round(total / (1024 ** 3), 3)}
    except Exception:
        return {"total_bytes": None, "total_gb": None}


def _gpu_info() -> dict[str, Any]:
    nvidia = shutil.which("nvidia-smi")
    if nvidia:
        try:
            proc = subprocess.run([nvidia, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], text=True, capture_output=True, timeout=5)
            if proc.returncode == 0:
                gpus = []
                for line in proc.stdout.splitlines():
                    if not line.strip():
                        continue
                    name, memory = [part.strip() for part in line.split(",", 1)]
                    gpus.append({"name": name, "memory_mb": int(float(memory)), "memory_gb": round(float(memory) / 1024, 3), "meets_2gb_minimum": float(memory) >= 2048})
                return {"available": bool(gpus), "backend": "nvidia-smi", "devices": gpus}
        except Exception as exc:
            return {"available": False, "backend": "nvidia-smi", "error": str(exc)}
    return {"available": False, "backend": None, "devices": [], "note": "No GPU runtime detected. AGILANG ML will use CPU fallback."}


def _coerce_number(value: Any) -> Any:
    if value in (None, ""):
        return value
    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except (TypeError, ValueError):
        return value


def _nearest(point: list[float], centroids: list[list[float]]) -> int:
    distances = [sum((a - b) ** 2 for a, b in zip(point, centroid)) for centroid in centroids]
    return distances.index(min(distances))


def _majority(values: Sequence[int]) -> int:
    if not values:
        return 0
    return 1 if sum(values) >= len(values) / 2 else 0


def _r2(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    ys = list(y_true)
    if not ys:
        return 0.0
    mean = sum(ys) / len(ys)
    ss_res = sum((y - p) ** 2 for y, p in zip(ys, y_pred))
    ss_tot = sum((y - mean) ** 2 for y in ys)
    return 1.0 if ss_tot == 0 and ss_res == 0 else (0.0 if ss_tot == 0 else 1 - ss_res / ss_tot)


__all__ = [
    "ai_runtime_info",
    "ml_accuracy",
    "ml_chart_spec",
    "ml_confusion_matrix",
    "ml_dataset_summary",
    "ml_decision_stump",
    "ml_fill_missing",
    "ml_kmeans",
    "ml_linear_regression",
    "ml_load_model",
    "ml_logistic_regression",
    "ml_minmax_scale",
    "ml_missing_values",
    "ml_neural_network_predict",
    "ml_neural_network_train",
    "ml_predict_linear",
    "ml_predict_logistic",
    "ml_predict_tree",
    "ml_read_csv",
    "ml_save_model",
    "ml_standard_scale",
    "ml_train_test_split",
    "ml_write_csv",
    "tensor_add",
    "tensor_dot",
    "tensor_matmul",
    "tensor_mean",
    "tensor_mul",
    "tensor_random",
    "tensor_relu",
    "tensor_shape",
    "tensor_sigmoid",
    "tensor_softmax",
    "tensor_sub",
    "tensor_transpose",
    "tensor_variance",
    "tensor_zeros",
]
