"""AGILANG multi-channel Conv2D training kernels.

This module extends CNN training from single-channel filters to RGB/multi-channel
and multi-filter Conv2D backward gradients. It is a correctness-first CPU
reference layer for AGILANG AIFlow.
"""
from __future__ import annotations

from typing import Any, Sequence

Image3D = list[list[list[float]]]
Kernel3D = list[list[list[float]]]
FeatureMaps = list[list[list[float]]]


def _to_float_3d(values: Sequence[Sequence[Sequence[float]]]) -> Image3D:
    return [[[float(c) for c in pixel] for pixel in row] for row in values]


def _zeros_3d(h: int, w: int, c: int) -> Image3D:
    return [[[0.0 for _ in range(c)] for _ in range(w)] for _ in range(h)]


def conv2d_multi_channel_forward(image: Sequence[Sequence[Sequence[float]]], kernel: Sequence[Sequence[Sequence[float]]], bias: float = 0.0, stride: int = 1) -> list[list[float]]:
    img = _to_float_3d(image)
    ker = _to_float_3d(kernel)
    if not img or not img[0] or not img[0][0]:
        return []
    h, w, channels = len(img), len(img[0]), len(img[0][0])
    kh, kw, kc = len(ker), len(ker[0]), len(ker[0][0])
    if kc != channels:
        raise ValueError("kernel channel count must match image channel count")
    out: list[list[float]] = []
    for i in range(0, h - kh + 1, stride):
        row = []
        for j in range(0, w - kw + 1, stride):
            total = float(bias)
            for ki in range(kh):
                for kj in range(kw):
                    for c in range(channels):
                        total += img[i + ki][j + kj][c] * ker[ki][kj][c]
            row.append(total)
        out.append(row)
    return out


def conv2d_multi_channel_backward(image: Sequence[Sequence[Sequence[float]]], kernel: Sequence[Sequence[Sequence[float]]], grad_output: Sequence[Sequence[float]], stride: int = 1) -> dict[str, Any]:
    img = _to_float_3d(image)
    ker = _to_float_3d(kernel)
    gout = [[float(v) for v in row] for row in grad_output]
    h, w, channels = len(img), len(img[0]), len(img[0][0])
    kh, kw, kc = len(ker), len(ker[0]), len(ker[0][0])
    if kc != channels:
        raise ValueError("kernel channel count must match image channel count")
    grad_image = _zeros_3d(h, w, channels)
    grad_kernel = _zeros_3d(kh, kw, channels)
    grad_bias = 0.0
    for oi, row in enumerate(gout):
        i = oi * stride
        for oj, gv in enumerate(row):
            j = oj * stride
            grad_bias += gv
            for ki in range(kh):
                for kj in range(kw):
                    for c in range(channels):
                        grad_kernel[ki][kj][c] += img[i + ki][j + kj][c] * gv
                        grad_image[i + ki][j + kj][c] += ker[ki][kj][c] * gv
    return {"grad_image": grad_image, "grad_kernel": grad_kernel, "grad_bias": grad_bias}


def conv2d_multi_filter_forward(image: Sequence[Sequence[Sequence[float]]], kernels: Sequence[Sequence[Sequence[Sequence[float]]]], biases: Sequence[float] | None = None, stride: int = 1) -> FeatureMaps:
    biases = [0.0 for _ in kernels] if biases is None else [float(v) for v in biases]
    return [conv2d_multi_channel_forward(image, kernel, bias=biases[idx] if idx < len(biases) else 0.0, stride=stride) for idx, kernel in enumerate(kernels)]


def conv2d_multi_filter_backward(image: Sequence[Sequence[Sequence[float]]], kernels: Sequence[Sequence[Sequence[Sequence[float]]]], grad_outputs: Sequence[Sequence[Sequence[float]]], stride: int = 1) -> dict[str, Any]:
    img = _to_float_3d(image)
    h, w, channels = len(img), len(img[0]), len(img[0][0])
    total_grad_image = _zeros_3d(h, w, channels)
    grad_kernels: list[Kernel3D] = []
    grad_biases: list[float] = []
    for kernel, grad_output in zip(kernels, grad_outputs):
        grads = conv2d_multi_channel_backward(img, kernel, grad_output, stride=stride)
        grad_kernels.append(grads["grad_kernel"])
        grad_biases.append(float(grads["grad_bias"]))
        for i in range(h):
            for j in range(w):
                for c in range(channels):
                    total_grad_image[i][j][c] += grads["grad_image"][i][j][c]
    return {"grad_image": total_grad_image, "grad_kernels": grad_kernels, "grad_biases": grad_biases}


def mse_feature_maps(predicted: Sequence[Sequence[Sequence[float]]], target: Sequence[Sequence[Sequence[float]]]) -> tuple[float, FeatureMaps]:
    count = 0
    loss = 0.0
    grad_outputs: FeatureMaps = []
    for fmap, tmap in zip(predicted, target):
        grad_map: list[list[float]] = []
        for prow, trow in zip(fmap, tmap):
            grow = []
            for p, t in zip(prow, trow):
                err = float(p) - float(t)
                loss += err * err
                count += 1
                grow.append(err)  # scaled below after count known
            grad_map.append(grow)
        grad_outputs.append(grad_map)
    count = max(1, count)
    for fmap in grad_outputs:
        for row in fmap:
            for idx, value in enumerate(row):
                row[idx] = (2.0 / count) * value
    return loss / count, grad_outputs


__all__ = [
    "conv2d_multi_channel_forward",
    "conv2d_multi_channel_backward",
    "conv2d_multi_filter_forward",
    "conv2d_multi_filter_backward",
    "mse_feature_maps",
]
