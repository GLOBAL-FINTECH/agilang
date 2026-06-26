"""AGILANG native CNN layer integration for AIFlow.

This module builds on vision_kernels_v2 and turns raw kernels into composable
CNN-style classifier helpers. It adds multi-filter RGB Conv2D forward execution,
feature concatenation, dense classification, and a small serializable CNN model.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .vision_kernels import flatten, maxpool2d, relu_image
from .vision_kernels_v2 import argmax, conv2d_multi_channel, dense_predict, softmax

RGBImage = list[list[list[float]]]
RGBKernel = list[list[list[float]]]


def conv2d_multi_filter(image: Sequence[Sequence[Sequence[float]]], kernels: Sequence[Sequence[Sequence[Sequence[float]]]], biases: Sequence[float] | None = None, stride: int = 1, padding: int = 0) -> list[list[list[float]]]:
    """Apply multiple RGB kernels and return one feature map per filter."""
    biases = [0.0 for _ in kernels] if biases is None else [float(v) for v in biases]
    maps: list[list[list[float]]] = []
    for idx, kernel in enumerate(kernels):
        maps.append(conv2d_multi_channel(image, kernel, stride=stride, padding=padding, bias=biases[idx] if idx < len(biases) else 0.0))
    return maps


def cnn_multi_filter_features(image: Sequence[Sequence[Sequence[float]]], kernels: Sequence[Sequence[Sequence[Sequence[float]]]], biases: Sequence[float] | None = None, pool_size: int = 2) -> dict[str, Any]:
    """Run multi-filter Conv2D -> ReLU -> MaxPool -> Flatten."""
    feature_maps = conv2d_multi_filter(image, kernels, biases=biases)
    activated = [relu_image(fmap) for fmap in feature_maps]
    pooled = [maxpool2d(fmap, pool_size=pool_size) if fmap else [] for fmap in activated]
    features: list[float] = []
    for fmap in pooled:
        features.extend(flatten(fmap))
    return {"feature_maps": feature_maps, "activated": activated, "pooled": pooled, "features": features}


@dataclass
class CNNClassifier:
    kernels: list[RGBKernel]
    dense_weights: list[list[float]]
    labels: list[str]
    conv_biases: list[float] = field(default_factory=list)
    dense_bias: list[float] = field(default_factory=list)
    pool_size: int = 2

    def predict(self, image: Sequence[Sequence[Sequence[float]]]) -> dict[str, Any]:
        features_result = cnn_multi_filter_features(image, self.kernels, biases=self.conv_biases, pool_size=self.pool_size)
        scores = dense_predict(features_result["features"], self.dense_weights, self.dense_bias or None)
        probabilities = softmax(scores)
        index = argmax(probabilities) if probabilities else -1
        return {"features": features_result["features"], "scores": scores, "probabilities": probabilities, "predicted_index": index, "predicted_label": self.labels[index] if 0 <= index < len(self.labels) else None}

    def save(self, path: str | Path) -> str:
        payload = {"format": "agilang-cnn-classifier", "kernels": self.kernels, "dense_weights": self.dense_weights, "labels": self.labels, "conv_biases": self.conv_biases, "dense_bias": self.dense_bias, "pool_size": self.pool_size}
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)

    @classmethod
    def load(cls, path: str | Path) -> "CNNClassifier":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(kernels=payload["kernels"], dense_weights=payload["dense_weights"], labels=payload["labels"], conv_biases=payload.get("conv_biases", []), dense_bias=payload.get("dense_bias", []), pool_size=int(payload.get("pool_size", 2)))


def load_cnn_classifier(path: str | Path) -> CNNClassifier:
    return CNNClassifier.load(path)


__all__ = ["conv2d_multi_filter", "cnn_multi_filter_features", "CNNClassifier", "load_cnn_classifier"]
