"""AGILANG native Conv2D training kernels.

This module adds correctness-first CPU/reference backward gradients for
single-channel Conv2D. It is the first step from CNN inference toward native CNN
training: filter gradients, input gradients, bias gradients, loss calculation,
and an SGD update step.
"""
from __future__ import annotations

from typing import Any, Sequence

Image2D = list[list[float]]
Kernel2D = list[list[float]]


def _to_float_2d(values: Sequence[Sequence[float]]) -> list[list[float]]:
    return [[float(v) for v in row] for row in values]


def conv2d_forward(image: Sequence[Sequence[float]], kernel: Sequence[Sequence[float]], bias: float = 0.0, stride: int = 1) -> Image2D:
    if stride <= 0:
        raise ValueError("stride must be positive")
    img = _to_float_2d(image)
    ker = _to_float_2d(kernel)
    if not img or not img[0] or not ker or not ker[0]:
        return []
    h, w = len(img), len(img[0])
    kh, kw = len(ker), len(ker[0])
    if h < kh or w < kw:
        return []
    out: Image2D = []
    for i in range(0, h - kh + 1, stride):
        row = []
        for j in range(0, w - kw + 1, stride):
            total = float(bias)
            for ki in range(kh):
                for kj in range(kw):
                    total += img[i + ki][j + kj] * ker[ki][kj]
            row.append(total)
        out.append(row)
    return out


def mse_loss(predicted: Sequence[Sequence[float]], target: Sequence[Sequence[float]]) -> tuple[float, Image2D]:
    pred = _to_float_2d(predicted)
    truth = _to_float_2d(target)
    if len(pred) != len(truth) or (pred and len(pred[0]) != len(truth[0])):
        raise ValueError("predicted and target shapes must match")
    count = max(1, sum(len(row) for row in pred))
    loss = 0.0
    grad: Image2D = []
    for prow, trow in zip(pred, truth):
        grow = []
        for p, t in zip(prow, trow):
            err = p - t
            loss += err * err
            grow.append((2.0 / count) * err)
        grad.append(grow)
    return loss / count, grad


def conv2d_backward(image: Sequence[Sequence[float]], kernel: Sequence[Sequence[float]], grad_output: Sequence[Sequence[float]], stride: int = 1) -> dict[str, Any]:
    """Return gradients for image, kernel, and bias.

    `grad_output` is dLoss/dConvOutput with the same shape as the forward output.
    """
    img = _to_float_2d(image)
    ker = _to_float_2d(kernel)
    gout = _to_float_2d(grad_output)
    h, w = len(img), len(img[0])
    kh, kw = len(ker), len(ker[0])
    grad_image = [[0.0 for _ in range(w)] for _ in range(h)]
    grad_kernel = [[0.0 for _ in range(kw)] for _ in range(kh)]
    grad_bias = 0.0
    for oi, row in enumerate(gout):
        i = oi * stride
        for oj, gv in enumerate(row):
            j = oj * stride
            grad_bias += gv
            for ki in range(kh):
                for kj in range(kw):
                    grad_kernel[ki][kj] += img[i + ki][j + kj] * gv
                    grad_image[i + ki][j + kj] += ker[ki][kj] * gv
    return {"grad_image": grad_image, "grad_kernel": grad_kernel, "grad_bias": grad_bias}


def sgd_update_kernel(kernel: Sequence[Sequence[float]], grad_kernel: Sequence[Sequence[float]], bias: float, grad_bias: float, learning_rate: float = 0.01) -> dict[str, Any]:
    ker = _to_float_2d(kernel)
    grad = _to_float_2d(grad_kernel)
    updated = []
    for row, grow in zip(ker, grad):
        updated.append([w - learning_rate * g for w, g in zip(row, grow)])
    return {"kernel": updated, "bias": float(bias) - learning_rate * float(grad_bias)}


def train_conv2d_step(image: Sequence[Sequence[float]], kernel: Sequence[Sequence[float]], target: Sequence[Sequence[float]], bias: float = 0.0, learning_rate: float = 0.01, stride: int = 1) -> dict[str, Any]:
    pred = conv2d_forward(image, kernel, bias=bias, stride=stride)
    loss, grad_output = mse_loss(pred, target)
    grads = conv2d_backward(image, kernel, grad_output, stride=stride)
    updated = sgd_update_kernel(kernel, grads["grad_kernel"], bias, grads["grad_bias"], learning_rate=learning_rate)
    return {"loss": loss, "prediction": pred, "grad_output": grad_output, "gradients": grads, "kernel": updated["kernel"], "bias": updated["bias"]}


__all__ = ["conv2d_forward", "mse_loss", "conv2d_backward", "sgd_update_kernel", "train_conv2d_step"]
