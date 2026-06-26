"""AGILANG native vision kernels for AIFlow.

This module adds dependency-light CNN-style forward operations for image and
video analysis pipelines. These kernels are CPU/reference implementations meant
for correctness first; future C/WASM/GPU kernels can replace the inner loops.
"""
from __future__ import annotations

from typing import Any, Sequence

Image2D = list[list[float]]
Image3D = list[list[list[float]]]


def image_shape(image: Any) -> list[int]:
    if not isinstance(image, list):
        return []
    if not image:
        return [0]
    if isinstance(image[0], list) and image[0] and isinstance(image[0][0], list):
        return [len(image), len(image[0]), len(image[0][0])]
    if isinstance(image[0], list):
        return [len(image), len(image[0])]
    return [len(image)]


def normalize_image(image: Sequence[Sequence[float]], scale: float = 255.0) -> Image2D:
    return [[float(pixel) / scale for pixel in row] for row in image]


def flatten(values: Any) -> list[float]:
    out: list[float] = []
    if isinstance(values, list):
        for value in values:
            out.extend(flatten(value))
    else:
        out.append(float(values))
    return out


def conv2d_single_channel(image: Sequence[Sequence[float]], kernel: Sequence[Sequence[float]], stride: int = 1, padding: int = 0, bias: float = 0.0) -> Image2D:
    if stride <= 0:
        raise ValueError("stride must be positive")
    img = [[float(v) for v in row] for row in image]
    ker = [[float(v) for v in row] for row in kernel]
    if not img or not img[0] or not ker or not ker[0]:
        return []
    if padding:
        width = len(img[0])
        zero = [0.0 for _ in range(width + 2 * padding)]
        padded: Image2D = [zero[:] for _ in range(padding)]
        for row in img:
            padded.append([0.0] * padding + row + [0.0] * padding)
        padded.extend([zero[:] for _ in range(padding)])
        img = padded
    h, w = len(img), len(img[0])
    kh, kw = len(ker), len(ker[0])
    if h < kh or w < kw:
        return []
    out: Image2D = []
    for i in range(0, h - kh + 1, stride):
        row = []
        for j in range(0, w - kw + 1, stride):
            total = bias
            for ki in range(kh):
                for kj in range(kw):
                    total += img[i + ki][j + kj] * ker[ki][kj]
            row.append(float(total))
        out.append(row)
    return out


def maxpool2d(image: Sequence[Sequence[float]], pool_size: int = 2, stride: int | None = None) -> Image2D:
    stride = stride or pool_size
    if pool_size <= 0 or stride <= 0:
        raise ValueError("pool_size and stride must be positive")
    img = [[float(v) for v in row] for row in image]
    if not img or not img[0]:
        return []
    h, w = len(img), len(img[0])
    out: Image2D = []
    for i in range(0, h - pool_size + 1, stride):
        row = []
        for j in range(0, w - pool_size + 1, stride):
            row.append(max(img[i + pi][j + pj] for pi in range(pool_size) for pj in range(pool_size)))
        out.append(row)
    return out


def avgpool2d(image: Sequence[Sequence[float]], pool_size: int = 2, stride: int | None = None) -> Image2D:
    stride = stride or pool_size
    img = [[float(v) for v in row] for row in image]
    if not img or not img[0]:
        return []
    out: Image2D = []
    for i in range(0, len(img) - pool_size + 1, stride):
        row = []
        for j in range(0, len(img[0]) - pool_size + 1, stride):
            vals = [img[i + pi][j + pj] for pi in range(pool_size) for pj in range(pool_size)]
            row.append(sum(vals) / len(vals))
        out.append(row)
    return out


def relu_image(image: Sequence[Sequence[float]]) -> Image2D:
    return [[max(0.0, float(v)) for v in row] for row in image]


def image_to_patches(image: Sequence[Sequence[float]], patch_size: int = 2, stride: int = 1) -> list[list[float]]:
    img = [[float(v) for v in row] for row in image]
    patches: list[list[float]] = []
    for i in range(0, len(img) - patch_size + 1, stride):
        for j in range(0, len(img[0]) - patch_size + 1, stride):
            patches.append([img[i + pi][j + pj] for pi in range(patch_size) for pj in range(patch_size)])
    return patches


def cnn_feature_pipeline(image: Sequence[Sequence[float]], kernel: Sequence[Sequence[float]], pool_size: int = 2) -> dict[str, Any]:
    normalized = normalize_image(image) if max(flatten(image) or [0.0]) > 1.0 else [[float(v) for v in row] for row in image]
    conv = conv2d_single_channel(normalized, kernel, padding=0)
    activated = relu_image(conv)
    pooled = maxpool2d(activated, pool_size=pool_size) if activated else []
    features = flatten(pooled)
    return {"input_shape": image_shape(image), "conv_shape": image_shape(conv), "pool_shape": image_shape(pooled), "features": features}


__all__ = [
    "image_shape",
    "normalize_image",
    "flatten",
    "conv2d_single_channel",
    "maxpool2d",
    "avgpool2d",
    "relu_image",
    "image_to_patches",
    "cnn_feature_pipeline",
]
