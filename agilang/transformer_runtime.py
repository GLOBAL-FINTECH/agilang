"""Production-facing transformer runtime primitives for AGILANG AIFlow.

This module remains dependency-free and CPU/reference by default, but it now
exposes a usable transformer inference surface instead of only tiny standalone
helpers. It supports embeddings, deterministic linear projections, multi-head
self-attention, causal masking, residual layer normalization, feed-forward
layers, serialization, and clear backend metadata.

For very large models, AGILANG should still use an external audited backend such
as PyTorch, ONNX Runtime, TensorRT, llama.cpp, or another production inference
engine through the interop layer. This file provides the small/medium native
runtime path and stable API contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import random
from pathlib import Path
from typing import Any, Sequence

TRANSFORMER_FORMAT = "agilang-transformer-runtime-v2"


# ---------------------------------------------------------------------------
# Base math helpers kept for compatibility
# ---------------------------------------------------------------------------

def layer_norm(values: Sequence[float], eps: float = 1e-5) -> list[float]:
    vals = [float(v) for v in values]
    mean = sum(vals) / max(1, len(vals))
    var = sum((v - mean) ** 2 for v in vals) / max(1, len(vals))
    return [(v - mean) / math.sqrt(var + eps) for v in vals]


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(x) * float(y) for x, y in zip(a, b))


def softmax(values: Sequence[float]) -> list[float]:
    vals = [float(v) for v in values]
    if not vals:
        return []
    top = max(vals)
    exps = [math.exp(v - top) for v in vals]
    total = sum(exps) or 1.0
    return [v / total for v in exps]


def attention_scores(query: Sequence[float], keys: Sequence[Sequence[float]], *, causal_index: int | None = None) -> list[float]:
    scale = math.sqrt(max(1, len(query)))
    raw: list[float] = []
    for i, key in enumerate(keys):
        if causal_index is not None and i > causal_index:
            raw.append(-1e30)
        else:
            raw.append(dot(query, key) / scale)
    return softmax(raw)


def attention_pool(query: Sequence[float], keys: Sequence[Sequence[float]], values: Sequence[Sequence[float]], *, causal_index: int | None = None) -> list[float]:
    weights = attention_scores(query, keys, causal_index=causal_index)
    dim = len(values[0]) if values else 0
    out = [0.0 for _ in range(dim)]
    for weight, value in zip(weights, values):
        for i in range(dim):
            out[i] += weight * float(value[i])
    return out


def feed_forward(values: Sequence[float], hidden_scale: float = 1.5) -> list[float]:
    return [max(0.0, float(v) * hidden_scale) for v in values]


def transformer_block(tokens: Sequence[Sequence[float]]) -> list[list[float]]:
    """Compatibility tiny block: one self-attention pool plus FFN."""
    out = []
    for i, token in enumerate(tokens):
        attended = attention_pool(token, tokens, tokens, causal_index=None)
        residual = [float(a) + float(b) for a, b in zip(token, attended)]
        normalized = layer_norm(residual)
        ff = feed_forward(normalized)
        out.append(layer_norm([a + b for a, b in zip(normalized, ff)]))
    return out


# ---------------------------------------------------------------------------
# Production-facing reference runtime
# ---------------------------------------------------------------------------

def _matrix(rows: int, cols: int, rnd: random.Random, scale: float = 0.02) -> list[list[float]]:
    return [[rnd.uniform(-scale, scale) for _ in range(cols)] for _ in range(rows)]


def _vector(size: int, value: float = 0.0) -> list[float]:
    return [float(value) for _ in range(size)]


def linear(values: Sequence[float], weights: Sequence[Sequence[float]], bias: Sequence[float] | None = None) -> list[float]:
    if not weights:
        return []
    out_dim = len(weights[0])
    out = [0.0 for _ in range(out_dim)]
    for i, value in enumerate(values):
        if i >= len(weights):
            break
        for j in range(out_dim):
            out[j] += float(value) * float(weights[i][j])
    if bias is not None:
        out = [v + float(bias[i]) for i, v in enumerate(out)]
    return out


def gelu(x: float) -> float:
    return 0.5 * x * (1.0 + math.tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * x ** 3)))


@dataclass
class TransformerConfig:
    vocab_size: int
    dim: int = 64
    heads: int = 4
    hidden_dim: int = 128
    layers: int = 2
    max_positions: int = 512
    causal: bool = True
    seed: int = 42

    def __post_init__(self) -> None:
        if self.vocab_size <= 0:
            raise ValueError("vocab_size must be positive")
        if self.dim <= 0 or self.hidden_dim <= 0 or self.layers <= 0:
            raise ValueError("dim, hidden_dim and layers must be positive")
        if self.heads <= 0 or self.dim % self.heads != 0:
            raise ValueError("heads must divide dim")

    def as_dict(self) -> dict[str, Any]:
        return {
            "vocab_size": self.vocab_size,
            "dim": self.dim,
            "heads": self.heads,
            "hidden_dim": self.hidden_dim,
            "layers": self.layers,
            "max_positions": self.max_positions,
            "causal": self.causal,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TransformerConfig":
        return cls(**{k: payload[k] for k in ["vocab_size", "dim", "heads", "hidden_dim", "layers", "max_positions", "causal", "seed"] if k in payload})


@dataclass
class TransformerLayerWeights:
    q: list[list[float]]
    k: list[list[float]]
    v: list[list[float]]
    o: list[list[float]]
    ff1: list[list[float]]
    ff1_bias: list[float]
    ff2: list[list[float]]
    ff2_bias: list[float]


@dataclass
class TransformerWeights:
    token_embedding: list[list[float]]
    position_embedding: list[list[float]]
    layers: list[TransformerLayerWeights]
    lm_head: list[list[float]]

    @classmethod
    def init(cls, config: TransformerConfig) -> "TransformerWeights":
        rnd = random.Random(config.seed)
        layers: list[TransformerLayerWeights] = []
        for _ in range(config.layers):
            layers.append(TransformerLayerWeights(
                q=_matrix(config.dim, config.dim, rnd),
                k=_matrix(config.dim, config.dim, rnd),
                v=_matrix(config.dim, config.dim, rnd),
                o=_matrix(config.dim, config.dim, rnd),
                ff1=_matrix(config.dim, config.hidden_dim, rnd),
                ff1_bias=_vector(config.hidden_dim),
                ff2=_matrix(config.hidden_dim, config.dim, rnd),
                ff2_bias=_vector(config.dim),
            ))
        return cls(
            token_embedding=_matrix(config.vocab_size, config.dim, rnd),
            position_embedding=_matrix(config.max_positions, config.dim, rnd),
            layers=layers,
            lm_head=_matrix(config.dim, config.vocab_size, rnd),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "token_embedding": self.token_embedding,
            "position_embedding": self.position_embedding,
            "layers": [layer.__dict__ for layer in self.layers],
            "lm_head": self.lm_head,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TransformerWeights":
        return cls(
            token_embedding=payload["token_embedding"],
            position_embedding=payload["position_embedding"],
            layers=[TransformerLayerWeights(**layer) for layer in payload.get("layers", [])],
            lm_head=payload["lm_head"],
        )


class ProductionTransformerRuntime:
    """Small transformer inference runtime with deterministic portable weights."""

    def __init__(self, config: TransformerConfig, weights: TransformerWeights | None = None) -> None:
        self.config = config
        self.weights = weights or TransformerWeights.init(config)

    @classmethod
    def create(cls, vocab_size: int, **kwargs: Any) -> "ProductionTransformerRuntime":
        return cls(TransformerConfig(vocab_size=vocab_size, **kwargs))

    def embed(self, token_ids: Sequence[int]) -> list[list[float]]:
        out: list[list[float]] = []
        for pos, token_id in enumerate(token_ids[: self.config.max_positions]):
            tid = int(token_id) % self.config.vocab_size
            pos_id = pos % self.config.max_positions
            out.append([a + b for a, b in zip(self.weights.token_embedding[tid], self.weights.position_embedding[pos_id])])
        return out

    def _multi_head_attention(self, tokens: list[list[float]], layer: TransformerLayerWeights) -> list[list[float]]:
        heads = self.config.heads
        head_dim = self.config.dim // heads
        queries = [linear(token, layer.q) for token in tokens]
        keys = [linear(token, layer.k) for token in tokens]
        values = [linear(token, layer.v) for token in tokens]
        attended_tokens: list[list[float]] = []
        for pos, query in enumerate(queries):
            joined: list[float] = []
            for head in range(heads):
                start = head * head_dim
                end = start + head_dim
                qh = query[start:end]
                kh = [key[start:end] for key in keys]
                vh = [value[start:end] for value in values]
                joined.extend(attention_pool(qh, kh, vh, causal_index=pos if self.config.causal else None))
            attended_tokens.append(linear(joined, layer.o))
        return attended_tokens

    def forward_hidden(self, token_ids: Sequence[int]) -> list[list[float]]:
        tokens = self.embed(token_ids)
        for layer in self.weights.layers:
            attn = self._multi_head_attention(tokens, layer)
            tokens = [layer_norm([a + b for a, b in zip(token, attended)]) for token, attended in zip(tokens, attn)]
            ff_hidden = [[gelu(v) for v in linear(token, layer.ff1, layer.ff1_bias)] for token in tokens]
            ff_out = [linear(hidden, layer.ff2, layer.ff2_bias) for hidden in ff_hidden]
            tokens = [layer_norm([a + b for a, b in zip(token, ff)]) for token, ff in zip(tokens, ff_out)]
        return tokens

    def logits(self, token_ids: Sequence[int]) -> list[list[float]]:
        return [linear(hidden, self.weights.lm_head) for hidden in self.forward_hidden(token_ids)]

    def predict_next(self, token_ids: Sequence[int]) -> dict[str, Any]:
        all_logits = self.logits(token_ids)
        last = all_logits[-1] if all_logits else [0.0 for _ in range(self.config.vocab_size)]
        probabilities = softmax(last)
        token_id = max(range(len(probabilities)), key=lambda i: probabilities[i]) if probabilities else 0
        return {"token_id": token_id, "probability": probabilities[token_id] if probabilities else 0.0, "probabilities": probabilities}

    def generate(self, token_ids: Sequence[int], steps: int = 16) -> list[int]:
        ids = [int(v) for v in token_ids]
        for _ in range(max(0, int(steps))):
            ids.append(int(self.predict_next(ids)["token_id"]))
        return ids

    def to_dict(self) -> dict[str, Any]:
        return {"format": TRANSFORMER_FORMAT, "config": self.config.as_dict(), "weights": self.weights.as_dict()}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProductionTransformerRuntime":
        if payload.get("format") not in {TRANSFORMER_FORMAT, None}:
            raise ValueError(f"unsupported transformer format: {payload.get('format')}")
        return cls(TransformerConfig.from_dict(payload["config"]), TransformerWeights.from_dict(payload["weights"]))

    def save(self, path: str | Path) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
        return str(p)

    @classmethod
    def load(cls, path: str | Path) -> "ProductionTransformerRuntime":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def summary(self) -> dict[str, Any]:
        return {"format": TRANSFORMER_FORMAT, "backend": "cpu-reference", **self.config.as_dict()}


def transformer_runtime(vocab_size: int, **kwargs: Any) -> ProductionTransformerRuntime:
    return ProductionTransformerRuntime.create(vocab_size, **kwargs)


def load_transformer_runtime(path: str | Path) -> ProductionTransformerRuntime:
    return ProductionTransformerRuntime.load(path)


__all__ = [
    "TRANSFORMER_FORMAT",
    "layer_norm",
    "dot",
    "softmax",
    "attention_scores",
    "attention_pool",
    "feed_forward",
    "transformer_block",
    "linear",
    "gelu",
    "TransformerConfig",
    "TransformerWeights",
    "TransformerLayerWeights",
    "ProductionTransformerRuntime",
    "transformer_runtime",
    "load_transformer_runtime",
]
