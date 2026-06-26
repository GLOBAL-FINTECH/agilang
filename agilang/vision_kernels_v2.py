"""AGILANG native vision kernels v2.

This layer adds RGB/multi-channel Conv2D, softmax classification helpers, and a
small end-to-end image classifier pipeline. The functions are reference CPU
implementations intended for correctness and developer education before native
C/WASM/GPU kernels replace the inner loops.
"""
from __future__ import annotations

import math
import time
from typing import Any, Sequence

from .vision_kernels import flatten, maxpool2d, normalize_image, relu_image

Image3D = list[list[list[float]]]
Kernel3D = list[list[list[float]]]


def softmax(scores: Sequence[float]) -> list[float]:
    vals = [float(v) for v in scores]
    if not vals:
        return []
    m = max(vals)
    exps = [math.exp(v - m) for v in vals]
    total = sum(exps) or 1.0
    return [v / total for v in exps]


def argmax(values: Sequence[float]) -> int:
    if not values:
        raise ValueError("argmax requires at least one value")
    return max(range(len(values)), key=lambda i: values[i])


def normalize_rgb(image: Sequence[Sequence[Sequence[float]]], scale: float = 255.0) -> Image3D:
    return [[[float(channel) / scale for channel in pixel] for pixel in row] for row in image]


def conv2d_multi_channel(image: Sequence[Sequence[Sequence[float]]], kernel: Sequence[Sequence[Sequence[float]]], stride: int = 1, padding: int = 0, bias: float = 0.0) -> list[list[float]]:
    if stride <= 0:
        raise ValueError("stride must be positive")
    img = normalize_rgb(image) if _max_nested(image) > 1.0 else [[[float(c) for c in px] for px in row] for row in image]
    ker = [[[float(c) for c in px] for px in row] for row in kernel]
    if not img or not img[0] or not img[0][0]:
        return []
    channels = len(img[0][0])
    kh, kw = len(ker), len(ker[0])
    if len(ker[0][0]) != channels:
        raise ValueError(f"kernel channels {len(ker[0][0])} do not match image channels {channels}")
    if padding:
        width = len(img[0])
        zero_px = [0.0 for _ in range(channels)]
        zero_row = [zero_px[:] for _ in range(width + 2 * padding)]
        padded: Image3D = [deepcopy_row(zero_row) for _ in range(padding)]
        for row in img:
            padded.append([zero_px[:] for _ in range(padding)] + [px[:] for px in row] + [zero_px[:] for _ in range(padding)])
        padded.extend([deepcopy_row(zero_row) for _ in range(padding)])
        img = padded
    h, w = len(img), len(img[0])
    if h < kh or w < kw:
        return []
    out: list[list[float]] = []
    for i in range(0, h - kh + 1, stride):
        row = []
        for j in range(0, w - kw + 1, stride):
            total = bias
            for ki in range(kh):
                for kj in range(kw):
                    for c in range(channels):
                        total += img[i + ki][j + kj][c] * ker[ki][kj][c]
            row.append(float(total))
        out.append(row)
    return out


def deepcopy_row(row: list[list[float]]) -> list[list[float]]:
    return [px[:] for px in row]


def _max_nested(value: Any) -> float:
    if isinstance(value, list):
        return max((_max_nested(v) for v in value), default=0.0)
    return float(value)


def dense_predict(features: Sequence[float], weights: Sequence[Sequence[float]], bias: Sequence[float] | None = None) -> list[float]:
    feats = [float(v) for v in features]
    if not weights:
        return []
    classes = len(weights[0])
    bias = [0.0 for _ in range(classes)] if bias is None else [float(v) for v in bias]
    scores = []
    for cls in range(classes):
        scores.append(sum(feats[i] * float(weights[i][cls]) for i in range(min(len(feats), len(weights)))) + bias[cls])
    return scores


def image_classifier_pipeline(image: Sequence[Sequence[Sequence[float]]], kernel: Sequence[Sequence[Sequence[float]]], weights: Sequence[Sequence[float]], labels: Sequence[str], bias: Sequence[float] | None = None, pool_size: int = 2) -> dict[str, Any]:
    conv = conv2d_multi_channel(image, kernel)
    activated = relu_image(conv)
    pooled = maxpool2d(activated, pool_size=pool_size) if activated else []
    features = flatten(pooled)
    scores = dense_predict(features, weights, bias)
    probabilities = softmax(scores)
    index = argmax(probabilities) if probabilities else -1
    return {
        "features": features,
        "scores": scores,
        "probabilities": probabilities,
        "predicted_index": index,
        "predicted_label": labels[index] if 0 <= index < len(labels) else None,
    }


def benchmark_conv2d(image: Sequence[Sequence[Sequence[float]]], kernel: Sequence[Sequence[Sequence[float]]], repeats: int = 10) -> dict[str, Any]:
    repeats = max(1, int(repeats))
    start = time.perf_counter()
    last = None
    for _ in range(repeats):
        last = conv2d_multi_channel(image, kernel)
    elapsed = time.perf_counter() - start
    return {"engine": "agilang-native-reference", "repeats": repeats, "seconds": elapsed, "seconds_per_run": elapsed / repeats, "output_shape": [len(last or []), len((last or [[]])[0]) if last else 0]}


__all__ = [
    "softmax",
    "argmax",
    "normalize_rgb",
    "conv2d_multi_channel",
    "dense_predict",
    "image_classifier_pipeline",
    "benchmark_conv2d",
]
