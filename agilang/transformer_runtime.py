"""Executable transformer runtime starter for AGILANG AIFlow."""
from __future__ import annotations

import math
from typing import Sequence


def layer_norm(values: Sequence[float], eps: float = 1e-5) -> list[float]:
    vals = [float(v) for v in values]
    mean = sum(vals) / max(1, len(vals))
    var = sum((v - mean) ** 2 for v in vals) / max(1, len(vals))
    return [(v - mean) / math.sqrt(var + eps) for v in vals]


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(x) * float(y) for x, y in zip(a, b))


def attention_scores(query: Sequence[float], keys: Sequence[Sequence[float]]) -> list[float]:
    scale = math.sqrt(max(1, len(query)))
    raw = [dot(query, key) / scale for key in keys]
    m = max(raw) if raw else 0.0
    exps = [math.exp(v - m) for v in raw]
    total = sum(exps) or 1.0
    return [v / total for v in exps]


def attention_pool(query: Sequence[float], keys: Sequence[Sequence[float]], values: Sequence[Sequence[float]]) -> list[float]:
    weights = attention_scores(query, keys)
    dim = len(values[0]) if values else 0
    out = [0.0 for _ in range(dim)]
    for weight, value in zip(weights, values):
        for i in range(dim):
            out[i] += weight * float(value[i])
    return out


def feed_forward(values: Sequence[float], hidden_scale: float = 1.5) -> list[float]:
    return [max(0.0, float(v) * hidden_scale) for v in values]


def transformer_block(tokens: Sequence[Sequence[float]]) -> list[list[float]]:
    out = []
    for token in tokens:
        attended = attention_pool(token, tokens, tokens)
        residual = [float(a) + float(b) for a, b in zip(token, attended)]
        normalized = layer_norm(residual)
        ff = feed_forward(normalized)
        out.append(layer_norm([a + b for a, b in zip(normalized, ff)]))
    return out


__all__ = ["layer_norm", "attention_scores", "attention_pool", "feed_forward", "transformer_block"]
