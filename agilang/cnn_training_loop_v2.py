"""AGILANG native CNN classifier training loop v2.

This module implements the second half of the native CNN training loop:

Conv2D -> ReLU -> MaxPool -> Flatten -> Dense classifier -> softmax loss ->
classifier backward -> feature gradients -> MaxPool backward -> ReLU backward ->
Conv2D backward -> Adam updates for kernels and dense weights.

It is a correctness-first CPU reference implementation for small CNN models.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .cnn_optimizers import AdamKernelState, adam_update_kernel, maxpool2d_backward, maxpool2d_forward_with_mask
from .cnn_training_loop_v1 import AdamMultiFilterState, adam_update_multifilter, relu_feature_maps, relu_feature_maps_backward
from .conv2d_multichannel_training import conv2d_multi_filter_backward, conv2d_multi_filter_forward
from .vision_kernels_v2 import softmax

FeatureMaps = list[list[list[float]]]
Kernel4D = list[list[list[list[float]]]]


def flatten_feature_maps(feature_maps: Sequence[Sequence[Sequence[float]]]) -> dict[str, Any]:
    values: list[float] = []
    shapes: list[tuple[int, int]] = []
    for fmap in feature_maps:
        rows = len(fmap)
        cols = len(fmap[0]) if fmap else 0
        shapes.append((rows, cols))
        for row in fmap:
            values.extend(float(v) for v in row)
    return {"values": values, "shapes": shapes}


def unflatten_feature_maps(values: Sequence[float], shapes: Sequence[tuple[int, int]]) -> FeatureMaps:
    idx = 0
    out: FeatureMaps = []
    for rows, cols in shapes:
        fmap: list[list[float]] = []
        for _ in range(rows):
            fmap.append([float(values[idx + j]) for j in range(cols)])
            idx += cols
        out.append(fmap)
    return out


def dense_forward(features: Sequence[float], weights: Sequence[Sequence[float]], bias: Sequence[float]) -> list[float]:
    classes = len(bias)
    scores: list[float] = []
    for cls in range(classes):
        scores.append(sum(float(features[i]) * float(weights[i][cls]) for i in range(len(features))) + float(bias[cls]))
    return scores


def softmax_cross_entropy(scores: Sequence[float], label_index: int) -> dict[str, Any]:
    probs = softmax(scores)
    if label_index < 0 or label_index >= len(probs):
        raise ValueError("label_index out of range")
    loss = -math.log(max(probs[label_index], 1e-12))
    grad_scores = list(probs)
    grad_scores[label_index] -= 1.0
    return {"loss": loss, "probabilities": probs, "grad_scores": grad_scores}


def dense_backward(features: Sequence[float], weights: Sequence[Sequence[float]], grad_scores: Sequence[float]) -> dict[str, Any]:
    grad_weights = [[0.0 for _ in grad_scores] for _ in features]
    grad_bias = [float(v) for v in grad_scores]
    grad_features = [0.0 for _ in features]
    for i, feature in enumerate(features):
        for cls, grad in enumerate(grad_scores):
            grad_weights[i][cls] += float(feature) * float(grad)
            grad_features[i] += float(weights[i][cls]) * float(grad)
    return {"grad_weights": grad_weights, "grad_bias": grad_bias, "grad_features": grad_features}


@dataclass
class AdamDenseState:
    m_weights: list[list[float]] = field(default_factory=list)
    v_weights: list[list[float]] = field(default_factory=list)
    m_bias: list[float] = field(default_factory=list)
    v_bias: list[float] = field(default_factory=list)
    t: int = 0

    def ensure_shape(self, weights: Sequence[Sequence[float]], bias: Sequence[float]) -> None:
        if self.m_weights and self.v_weights:
            return
        self.m_weights = [[0.0 for _ in row] for row in weights]
        self.v_weights = [[0.0 for _ in row] for row in weights]
        self.m_bias = [0.0 for _ in bias]
        self.v_bias = [0.0 for _ in bias]


def adam_update_dense(weights: Sequence[Sequence[float]], grad_weights: Sequence[Sequence[float]], bias: Sequence[float], grad_bias: Sequence[float], state: AdamDenseState | None = None, learning_rate: float = 0.001, beta1: float = 0.9, beta2: float = 0.999, epsilon: float = 1e-8) -> dict[str, Any]:
    state = state or AdamDenseState()
    state.ensure_shape(weights, bias)
    state.t += 1
    updated_weights: list[list[float]] = []
    for i, row in enumerate(weights):
        out_row = []
        for j, weight in enumerate(row):
            grad = float(grad_weights[i][j])
            state.m_weights[i][j] = beta1 * state.m_weights[i][j] + (1.0 - beta1) * grad
            state.v_weights[i][j] = beta2 * state.v_weights[i][j] + (1.0 - beta2) * grad * grad
            m_hat = state.m_weights[i][j] / (1.0 - beta1 ** state.t)
            v_hat = state.v_weights[i][j] / (1.0 - beta2 ** state.t)
            out_row.append(float(weight) - learning_rate * m_hat / (math.sqrt(v_hat) + epsilon))
        updated_weights.append(out_row)
    updated_bias: list[float] = []
    for j, value in enumerate(bias):
        grad = float(grad_bias[j])
        state.m_bias[j] = beta1 * state.m_bias[j] + (1.0 - beta1) * grad
        state.v_bias[j] = beta2 * state.v_bias[j] + (1.0 - beta2) * grad * grad
        m_hat = state.m_bias[j] / (1.0 - beta1 ** state.t)
        v_hat = state.v_bias[j] / (1.0 - beta2 ** state.t)
        updated_bias.append(float(value) - learning_rate * m_hat / (math.sqrt(v_hat) + epsilon))
    return {"weights": updated_weights, "bias": updated_bias, "state": state}


@dataclass
class NativeCNNClassifierV2:
    kernels: Kernel4D
    dense_weights: list[list[float]]
    labels: list[str]
    conv_biases: list[float] = field(default_factory=list)
    dense_bias: list[float] = field(default_factory=list)
    pool_size: int = 2
    conv_state: AdamMultiFilterState | None = None
    dense_state: AdamDenseState | None = None

    def __post_init__(self) -> None:
        if not self.conv_biases:
            self.conv_biases = [0.0 for _ in self.kernels]
        if not self.dense_bias:
            self.dense_bias = [0.0 for _ in self.labels]

    @classmethod
    def create(cls, kernels: Kernel4D, labels: Sequence[str], feature_count: int, seed: int = 42, pool_size: int = 2) -> "NativeCNNClassifierV2":
        rnd = random.Random(seed)
        dense_weights = [[rnd.uniform(-0.1, 0.1) for _ in labels] for _ in range(feature_count)]
        return cls(kernels=kernels, dense_weights=dense_weights, labels=list(labels), pool_size=pool_size)

    def forward(self, image: Sequence[Sequence[Sequence[float]]]) -> dict[str, Any]:
        conv = conv2d_multi_filter_forward(image, self.kernels, biases=self.conv_biases)
        relu = relu_feature_maps(conv)
        pooled = []
        pool_masks = []
        pool_shapes = []
        for fmap in relu["output"]:
            pool = maxpool2d_forward_with_mask(fmap, pool_size=self.pool_size)
            pooled.append(pool["output"])
            pool_masks.append(pool["mask"])
            pool_shapes.append(pool["input_shape"])
        flat = flatten_feature_maps(pooled)
        scores = dense_forward(flat["values"], self.dense_weights, self.dense_bias)
        probs = softmax(scores)
        return {"conv": conv, "relu": relu, "pooled": pooled, "pool_masks": pool_masks, "pool_shapes": pool_shapes, "flat": flat, "scores": scores, "probabilities": probs}

    def predict(self, image: Sequence[Sequence[Sequence[float]]]) -> dict[str, Any]:
        result = self.forward(image)
        probs = result["probabilities"]
        index = max(range(len(probs)), key=lambda i: probs[i]) if probs else -1
        return {"probabilities": probs, "predicted_index": index, "predicted_label": self.labels[index] if 0 <= index < len(self.labels) else None}

    def train_step(self, image: Sequence[Sequence[Sequence[float]]], label_index: int, learning_rate: float = 0.001) -> dict[str, Any]:
        fwd = self.forward(image)
        loss_result = softmax_cross_entropy(fwd["scores"], label_index)
        dense_grads = dense_backward(fwd["flat"]["values"], self.dense_weights, loss_result["grad_scores"])
        grad_pooled = unflatten_feature_maps(dense_grads["grad_features"], fwd["flat"]["shapes"])
        grad_relu = []
        for grad_map, mask, input_shape in zip(grad_pooled, fwd["pool_masks"], fwd["pool_shapes"]):
            grad_relu.append(maxpool2d_backward(grad_map, mask, input_shape))
        grad_conv = relu_feature_maps_backward(grad_relu, fwd["relu"]["mask"])
        conv_grads = conv2d_multi_filter_backward(image, self.kernels, grad_conv)
        dense_update = adam_update_dense(self.dense_weights, dense_grads["grad_weights"], self.dense_bias, dense_grads["grad_bias"], state=self.dense_state, learning_rate=learning_rate)
        conv_update = adam_update_multifilter(self.kernels, conv_grads["grad_kernels"], self.conv_biases, conv_grads["grad_biases"], state=self.conv_state, learning_rate=learning_rate)
        self.dense_weights = dense_update["weights"]
        self.dense_bias = dense_update["bias"]
        self.dense_state = dense_update["state"]
        self.kernels = conv_update["kernels"]
        self.conv_biases = conv_update["biases"]
        self.conv_state = conv_update["state"]
        return {"loss": loss_result["loss"], "probabilities": loss_result["probabilities"], "predicted": self.predict(image)}

    def fit(self, images: Sequence[Any], labels: Sequence[int], epochs: int = 1, learning_rate: float = 0.001) -> dict[str, list[float]]:
        history = {"loss": []}
        for _ in range(epochs):
            total = 0.0
            for image, label in zip(images, labels):
                total += self.train_step(image, int(label), learning_rate=learning_rate)["loss"]
            history["loss"].append(total / max(1, len(images)))
        return history

    def save(self, path: str | Path) -> str:
        payload = {"format": "agilang-native-cnn-v2", "kernels": self.kernels, "conv_biases": self.conv_biases, "dense_weights": self.dense_weights, "dense_bias": self.dense_bias, "labels": self.labels, "pool_size": self.pool_size}
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)

    @classmethod
    def load(cls, path: str | Path) -> "NativeCNNClassifierV2":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(kernels=payload["kernels"], dense_weights=payload["dense_weights"], labels=payload["labels"], conv_biases=payload.get("conv_biases", []), dense_bias=payload.get("dense_bias", []), pool_size=int(payload.get("pool_size", 2)))


def load_native_cnn_v2(path: str | Path) -> NativeCNNClassifierV2:
    return NativeCNNClassifierV2.load(path)


__all__ = ["flatten_feature_maps", "unflatten_feature_maps", "dense_forward", "softmax_cross_entropy", "dense_backward", "AdamDenseState", "adam_update_dense", "NativeCNNClassifierV2", "load_native_cnn_v2"]
