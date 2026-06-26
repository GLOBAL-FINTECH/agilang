"""AGILANG CNN training optimizers and pooling gradients.

This module extends the native CNN training stack with Adam updates for Conv2D
kernels and MaxPool2D backward gradient routing. The implementation is small,
deterministic, and dependency-free so it can serve as a correctness baseline
before C, WASM, or GPU kernels are added.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

Image2D = list[list[float]]
Kernel2D = list[list[float]]


def _zeros_like_2d(values: Sequence[Sequence[float]]) -> list[list[float]]:
    return [[0.0 for _ in row] for row in values]


def _to_float_2d(values: Sequence[Sequence[float]]) -> list[list[float]]:
    return [[float(v) for v in row] for row in values]


def maxpool2d_forward_with_mask(image: Sequence[Sequence[float]], pool_size: int = 2, stride: int | None = None) -> dict[str, Any]:
    """Run MaxPool2D forward and record the max positions for backpropagation."""
    stride = stride or pool_size
    if pool_size <= 0 or stride <= 0:
        raise ValueError("pool_size and stride must be positive")
    img = _to_float_2d(image)
    if not img or not img[0]:
        return {"output": [], "mask": [], "input_shape": [0, 0], "pool_size": pool_size, "stride": stride}
    out: Image2D = []
    mask: list[list[tuple[int, int]]] = []
    h, w = len(img), len(img[0])
    for i in range(0, h - pool_size + 1, stride):
        out_row = []
        mask_row = []
        for j in range(0, w - pool_size + 1, stride):
            best = img[i][j]
            best_pos = (i, j)
            for pi in range(pool_size):
                for pj in range(pool_size):
                    value = img[i + pi][j + pj]
                    if value > best:
                        best = value
                        best_pos = (i + pi, j + pj)
            out_row.append(best)
            mask_row.append(best_pos)
        out.append(out_row)
        mask.append(mask_row)
    return {"output": out, "mask": mask, "input_shape": [h, w], "pool_size": pool_size, "stride": stride}


def maxpool2d_backward(grad_output: Sequence[Sequence[float]], mask: Sequence[Sequence[tuple[int, int]]], input_shape: Sequence[int]) -> Image2D:
    """Route MaxPool2D gradients back only to the selected max positions."""
    h, w = int(input_shape[0]), int(input_shape[1])
    grad_input = [[0.0 for _ in range(w)] for _ in range(h)]
    for i, row in enumerate(grad_output):
        for j, grad in enumerate(row):
            mi, mj = mask[i][j]
            grad_input[mi][mj] += float(grad)
    return grad_input


@dataclass
class AdamKernelState:
    """State for Adam optimizer over a 2D kernel and scalar bias."""

    m_kernel: Kernel2D = field(default_factory=list)
    v_kernel: Kernel2D = field(default_factory=list)
    m_bias: float = 0.0
    v_bias: float = 0.0
    t: int = 0

    def ensure_shape(self, kernel: Sequence[Sequence[float]]) -> None:
        if self.m_kernel and self.v_kernel:
            return
        self.m_kernel = _zeros_like_2d(kernel)
        self.v_kernel = _zeros_like_2d(kernel)


def adam_update_kernel(
    kernel: Sequence[Sequence[float]],
    grad_kernel: Sequence[Sequence[float]],
    bias: float,
    grad_bias: float,
    state: AdamKernelState | None = None,
    learning_rate: float = 0.001,
    beta1: float = 0.9,
    beta2: float = 0.999,
    epsilon: float = 1e-8,
) -> dict[str, Any]:
    """Apply Adam update to a Conv2D kernel and bias."""
    ker = _to_float_2d(kernel)
    grad = _to_float_2d(grad_kernel)
    state = state or AdamKernelState()
    state.ensure_shape(ker)
    state.t += 1
    updated: Kernel2D = []
    for i, row in enumerate(ker):
        out_row = []
        for j, weight in enumerate(row):
            g = grad[i][j]
            state.m_kernel[i][j] = beta1 * state.m_kernel[i][j] + (1.0 - beta1) * g
            state.v_kernel[i][j] = beta2 * state.v_kernel[i][j] + (1.0 - beta2) * g * g
            m_hat = state.m_kernel[i][j] / (1.0 - beta1 ** state.t)
            v_hat = state.v_kernel[i][j] / (1.0 - beta2 ** state.t)
            out_row.append(weight - learning_rate * m_hat / (math.sqrt(v_hat) + epsilon))
        updated.append(out_row)
    gb = float(grad_bias)
    state.m_bias = beta1 * state.m_bias + (1.0 - beta1) * gb
    state.v_bias = beta2 * state.v_bias + (1.0 - beta2) * gb * gb
    m_bias_hat = state.m_bias / (1.0 - beta1 ** state.t)
    v_bias_hat = state.v_bias / (1.0 - beta2 ** state.t)
    updated_bias = float(bias) - learning_rate * m_bias_hat / (math.sqrt(v_bias_hat) + epsilon)
    return {"kernel": updated, "bias": updated_bias, "state": state}


__all__ = ["AdamKernelState", "adam_update_kernel", "maxpool2d_forward_with_mask", "maxpool2d_backward"]
