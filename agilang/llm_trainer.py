"""Native LLM trainer reference pipeline for AGILANG AIFlow.

This module provides a compact language-model training scaffold built around
AGILANG tokenizers and transformer runtime primitives. It is a CPU reference
trainer for tiny educational models, not a production LLM engine yet.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .bpe_tokenizer import BPETokenizer


@dataclass
class TinyLanguageModel:
    vocab_size: int
    transition: list[list[float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.transition:
            self.transition = [[0.0 for _ in range(self.vocab_size)] for _ in range(self.vocab_size)]

    def predict_next(self, token_id: int) -> int:
        row = self.transition[int(token_id)]
        return max(range(len(row)), key=lambda i: row[i]) if row else 0

    def train_pair(self, current_id: int, next_id: int, learning_rate: float = 0.1) -> float:
        current_id = int(current_id)
        next_id = int(next_id)
        scores = self.transition[current_id]
        predicted = self.predict_next(current_id)
        loss = 0.0 if predicted == next_id else 1.0
        for idx in range(self.vocab_size):
            target = 1.0 if idx == next_id else 0.0
            self.transition[current_id][idx] += learning_rate * (target - scores[idx])
        return loss

    def generate(self, start_id: int, steps: int = 5) -> list[int]:
        ids = [int(start_id)]
        for _ in range(steps):
            ids.append(self.predict_next(ids[-1]))
        return ids

    def save(self, path: str | Path) -> str:
        payload = {"format": "agilang-tiny-lm", "vocab_size": self.vocab_size, "transition": self.transition}
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(p)

    @classmethod
    def load(cls, path: str | Path) -> "TinyLanguageModel":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(int(payload["vocab_size"]), payload["transition"])


def train_tiny_lm(texts: Sequence[str], merges: int = 20, epochs: int = 3, learning_rate: float = 0.1) -> dict[str, Any]:
    tokenizer = BPETokenizer.train(texts, merges=merges)
    model = TinyLanguageModel(max(1, len(tokenizer.vocab)))
    pairs: list[tuple[int, int]] = []
    for text in texts:
        ids = tokenizer.encode(text)
        pairs.extend((ids[i], ids[i + 1]) for i in range(len(ids) - 1))
    history = {"loss": []}
    for epoch in range(epochs):
        random.Random(epoch).shuffle(pairs)
        total = 0.0
        for current_id, next_id in pairs:
            total += model.train_pair(current_id, next_id, learning_rate=learning_rate)
        history["loss"].append(total / max(1, len(pairs)))
    return {"tokenizer": tokenizer, "model": model, "history": history}


def load_tiny_lm(path: str | Path) -> TinyLanguageModel:
    return TinyLanguageModel.load(path)


__all__ = ["TinyLanguageModel", "train_tiny_lm", "load_tiny_lm"]
