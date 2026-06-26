"""AGILANG native CNN training loop v1.

This module implements the first half of the full CNN training loop:

RGB/multi-filter Conv2D -> ReLU -> feature-map MSE loss -> ReLU backward ->
multi-filter Conv2D backward -> Adam update for RGB kernels.

The second half will connect MaxPool, Flatten, Dense classifier, softmax loss,
and full end-to-end classifier training.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

from .conv2d_multichannel_training import (
    conv2d_multi_filter_backward,
    conv2d_multi_filter_forward,
    mse_feature_maps,
)

FeatureMaps = list[list[list[float]]]
Kernel3D = list[list[list[float]]]


def relu_feature_maps(feature_maps: Sequence[Sequence[Sequence[float]]]) -> dict[str, Any]:
    """Apply ReLU and keep the activation mask for backward pass."""
    activated: FeatureMaps = []
    mask: FeatureMaps = []
    for fmap in feature_maps:
        out_map: list[list[float]] = []
        mask_map: list[list[float]] = []
        for row in fmap:
            out_row = []
            mask_row = []
            for value in row:
                v = float(value)
                out_row.append(max(0.0, v))
                # Let zero-initialized filters receive a first learning signal.
                mask_row.append(1.0 if v >= 0.0 else 0.0)
            out_map.append(out_row)
            mask_map.append(mask_row)
        activated.append(out_map)
        mask.append(mask_map)
    return {"output": activated, "mask": mask}


def relu_feature_maps_backward(grad_output: Sequence[Sequence[Sequence[float]]], mask: Sequence[Sequence[Sequence[float]]]) -> FeatureMaps:
    """Route gradients only through positions active during ReLU forward."""
    grad_input: FeatureMaps = []
    for fmap_grad, fmap_mask in zip(grad_output, mask):
        out_map: list[list[float]] = []
        for grow, mrow in zip(fmap_grad, fmap_mask):
            out_map.append([float(g) * float(m) for g, m in zip(grow, mrow)])
        grad_input.append(out_map)
    return grad_input


@dataclass
class AdamMultiFilterState:
    """Adam optimizer state for multiple RGB Conv2D filters and biases."""

    m_kernels: list[Kernel3D] = field(default_factory=list)
    v_kernels: list[Kernel3D] = field(default_factory=list)
    m_biases: list[float] = field(default_factory=list)
    v_biases: list[float] = field(default_factory=list)
    t: int = 0

    def ensure_shape(self, kernels: Sequence[Sequence[Sequence[Sequence[float]]]]) -> None:
        if self.m_kernels and self.v_kernels:
            return
        self.m_kernels = [_zeros_like_kernel(kernel) for kernel in kernels]
        self.v_kernels = [_zeros_like_kernel(kernel) for kernel in kernels]
        self.m_biases = [0.0 for _ in kernels]
        self.v_biases = [0.0 for _ in kernels]


def _zeros_like_kernel(kernel: Sequence[Sequence[Sequence[float]]]) -> Kernel3D:
    return [[[0.0 for _ in pixel] for pixel in row] for row in kernel]


def adam_update_multifilter(
    kernels: Sequence[Sequence[Sequence[Sequence[float]]]],
    grad_kernels: Sequence[Sequence[Sequence[Sequence[float]]]],
    biases: Sequence[float],
    grad_biases: Sequence[float],
    state: AdamMultiFilterState | None = None,
    learning_rate: float = 0.001,
    beta1: float = 0.9,
    beta2: float = 0.999,
    epsilon: float = 1e-8,
) -> dict[str, Any]:
    """Apply Adam update to multi-filter RGB kernels and biases."""
    state = state or AdamMultiFilterState()
    state.ensure_shape(kernels)
    state.t += 1
    updated_kernels: list[Kernel3D] = []
    for fidx, kernel in enumerate(kernels):
        updated_kernel: Kernel3D = []
        for i, row in enumerate(kernel):
            updated_row: list[list[float]] = []
            for j, pixel in enumerate(row):
                updated_pixel: list[float] = []
                for c, weight in enumerate(pixel):
                    grad = float(grad_kernels[fidx][i][j][c])
                    state.m_kernels[fidx][i][j][c] = beta1 * state.m_kernels[fidx][i][j][c] + (1.0 - beta1) * grad
                    state.v_kernels[fidx][i][j][c] = beta2 * state.v_kernels[fidx][i][j][c] + (1.0 - beta2) * grad * grad
                    m_hat = state.m_kernels[fidx][i][j][c] / (1.0 - beta1 ** state.t)
                    v_hat = state.v_kernels[fidx][i][j][c] / (1.0 - beta2 ** state.t)
                    updated_pixel.append(float(weight) - learning_rate * m_hat / (math.sqrt(v_hat) + epsilon))
                updated_row.append(updated_pixel)
            updated_kernel.append(updated_row)
        updated_kernels.append(updated_kernel)
    updated_biases: list[float] = []
    for idx, bias in enumerate(biases):
        grad = float(grad_biases[idx])
        state.m_biases[idx] = beta1 * state.m_biases[idx] + (1.0 - beta1) * grad
        state.v_biases[idx] = beta2 * state.v_biases[idx] + (1.0 - beta2) * grad * grad
        m_hat = state.m_biases[idx] / (1.0 - beta1 ** state.t)
        v_hat = state.v_biases[idx] / (1.0 - beta2 ** state.t)
        updated_biases.append(float(bias) - learning_rate * m_hat / (math.sqrt(v_hat) + epsilon))
    return {"kernels": updated_kernels, "biases": updated_biases, "state": state}


def train_cnn_feature_step(
    image: Sequence[Sequence[Sequence[float]]],
    kernels: Sequence[Sequence[Sequence[Sequence[float]]]],
    target_feature_maps: Sequence[Sequence[Sequence[float]]],
    biases: Sequence[float] | None = None,
    optimizer_state: AdamMultiFilterState | None = None,
    learning_rate: float = 0.001,
) -> dict[str, Any]:
    """Train the Conv2D + ReLU feature extractor for one image/target step."""
    biases = [0.0 for _ in kernels] if biases is None else [float(v) for v in biases]
    conv = conv2d_multi_filter_forward(image, kernels, biases=biases)
    relu = relu_feature_maps(conv)
    loss, grad_relu_output = mse_feature_maps(relu["output"], target_feature_maps)
    grad_conv_output = relu_feature_maps_backward(grad_relu_output, relu["mask"])
    grads = conv2d_multi_filter_backward(image, kernels, grad_conv_output)
    updated = adam_update_multifilter(
        kernels,
        grads["grad_kernels"],
        biases,
        grads["grad_biases"],
        state=optimizer_state,
        learning_rate=learning_rate,
    )
    return {
        "loss": loss,
        "conv": conv,
        "relu": relu["output"],
        "grad_conv_output": grad_conv_output,
        "gradients": grads,
        "kernels": updated["kernels"],
        "biases": updated["biases"],
        "optimizer_state": updated["state"],
    }


__all__ = [
    "relu_feature_maps",
    "relu_feature_maps_backward",
    "AdamMultiFilterState",
    "adam_update_multifilter",
    "train_cnn_feature_step",
]
