"""Transformer block descriptors for AGILANG AIFlow.

These descriptors define the native LLM roadmap surface: embedding, attention,
layer normalization and feed-forward blocks. Execution kernels will be added in
the remaining final stage.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EmbeddingSpec:
    vocab_size: int
    dim: int

    def as_dict(self) -> dict[str, Any]:
        return {"type": "Embedding", "vocab_size": self.vocab_size, "dim": self.dim}


@dataclass
class AttentionSpec:
    heads: int
    dim: int

    def as_dict(self) -> dict[str, Any]:
        return {"type": "MultiHeadAttention", "heads": self.heads, "dim": self.dim}


@dataclass
class FeedForwardSpec:
    dim: int
    hidden_dim: int
    activation: str = "gelu"

    def as_dict(self) -> dict[str, Any]:
        return {"type": "FeedForward", "dim": self.dim, "hidden_dim": self.hidden_dim, "activation": self.activation}


@dataclass
class TransformerBlockSpec:
    dim: int
    heads: int
    hidden_dim: int

    def as_dict(self) -> dict[str, Any]:
        return {"type": "TransformerBlock", "attention": AttentionSpec(self.heads, self.dim).as_dict(), "feed_forward": FeedForwardSpec(self.dim, self.hidden_dim).as_dict(), "normalization": "layer_norm", "residual": True}


def transformer_stack(vocab_size: int, dim: int, heads: int, hidden_dim: int, layers: int) -> dict[str, Any]:
    return {"embedding": EmbeddingSpec(vocab_size, dim).as_dict(), "blocks": [TransformerBlockSpec(dim, heads, hidden_dim).as_dict() for _ in range(layers)], "output": {"type": "language_model_head", "vocab_size": vocab_size}}


__all__ = ["EmbeddingSpec", "AttentionSpec", "FeedForwardSpec", "TransformerBlockSpec", "transformer_stack"]
