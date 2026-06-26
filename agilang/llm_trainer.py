"""Production-facing lightweight language-model training for AGILANG AIFlow.

This module no longer presents the LLM layer as a toy-only transition table. It
keeps a dependency-free CPU model for small production workloads while exposing a
stable model bundle API: tokenizer persistence, n-gram smoothing, generation,
perplexity, save/load, and clear backend metadata.

For large LLM fine-tuning, AGILANG should delegate to a real backend such as
PyTorch, llama.cpp, ONNX Runtime GenAI, vLLM, or TensorRT-LLM through interop.
This module is the native small-model path, not a claim of GPT-scale training.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
import json
import math
import random
from pathlib import Path
from typing import Any, Sequence

from .bpe_tokenizer import BPETokenizer
from .transformer_runtime import ProductionTransformerRuntime, TransformerConfig

LANGUAGE_MODEL_FORMAT = "agilang-language-model-v2"


@dataclass
class TinyLanguageModel:
    """Backward-compatible bigram model retained for existing callers."""

    vocab_size: int
    transition: list[list[float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.transition:
            self.transition = [[0.0 for _ in range(self.vocab_size)] for _ in range(self.vocab_size)]

    def predict_next(self, token_id: int) -> int:
        row = self.transition[int(token_id) % self.vocab_size]
        return max(range(len(row)), key=lambda i: row[i]) if row else 0

    def train_pair(self, current_id: int, next_id: int, learning_rate: float = 0.1) -> float:
        current_id = int(current_id) % self.vocab_size
        next_id = int(next_id) % self.vocab_size
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


@dataclass
class NGramLanguageModel:
    """Smoothed n-gram language model suitable for small domain text products."""

    order: int
    vocab_size: int
    counts: dict[str, dict[str, int]] = field(default_factory=dict)
    context_totals: dict[str, int] = field(default_factory=dict)
    alpha: float = 0.1

    def __post_init__(self) -> None:
        self.order = max(1, int(self.order))
        self.vocab_size = max(1, int(self.vocab_size))
        self.alpha = max(1e-12, float(self.alpha))
        self.counts = {str(k): {str(t): int(v) for t, v in vals.items()} for k, vals in self.counts.items()}
        self.context_totals = {str(k): int(v) for k, v in self.context_totals.items()}

    def _context_key(self, context: Sequence[int]) -> str:
        n = max(0, self.order - 1)
        items = [int(v) % self.vocab_size for v in list(context)[-n:]] if n else []
        return ",".join(str(v) for v in items)

    def train_sequence(self, token_ids: Sequence[int]) -> None:
        ids = [int(v) % self.vocab_size for v in token_ids]
        for i, token_id in enumerate(ids):
            context = ids[max(0, i - self.order + 1):i]
            key = self._context_key(context)
            self.counts.setdefault(key, {})[str(token_id)] = self.counts.setdefault(key, {}).get(str(token_id), 0) + 1
            self.context_totals[key] = self.context_totals.get(key, 0) + 1

    def probability(self, context: Sequence[int], token_id: int) -> float:
        key = self._context_key(context)
        counts = self.counts.get(key, {})
        total = self.context_totals.get(key, 0)
        return (counts.get(str(int(token_id) % self.vocab_size), 0) + self.alpha) / (total + self.alpha * self.vocab_size)

    def distribution(self, context: Sequence[int]) -> list[float]:
        probs = [self.probability(context, i) for i in range(self.vocab_size)]
        total = sum(probs) or 1.0
        return [p / total for p in probs]

    def predict_next(self, context: Sequence[int]) -> int:
        dist = self.distribution(context)
        return max(range(len(dist)), key=lambda i: dist[i]) if dist else 0

    def sample_next(self, context: Sequence[int], *, temperature: float = 1.0, seed: int | None = None) -> int:
        rnd = random.Random(seed)
        temp = max(1e-6, float(temperature))
        dist = self.distribution(context)
        adjusted = [p ** (1.0 / temp) for p in dist]
        total = sum(adjusted) or 1.0
        threshold = rnd.random()
        acc = 0.0
        for idx, value in enumerate(adjusted):
            acc += value / total
            if threshold <= acc:
                return idx
        return len(adjusted) - 1 if adjusted else 0

    def generate(self, prompt_ids: Sequence[int], steps: int = 32, *, temperature: float = 1.0, seed: int | None = None) -> list[int]:
        ids = [int(v) % self.vocab_size for v in prompt_ids]
        rnd = random.Random(seed)
        for _ in range(max(0, int(steps))):
            ids.append(self.sample_next(ids, temperature=temperature, seed=rnd.randint(0, 2**31 - 1)))
        return ids

    def negative_log_likelihood(self, token_ids: Sequence[int]) -> float:
        ids = [int(v) % self.vocab_size for v in token_ids]
        if len(ids) < 2:
            return 0.0
        total = 0.0
        count = 0
        for i in range(1, len(ids)):
            context = ids[max(0, i - self.order + 1):i]
            total += -math.log(max(self.probability(context, ids[i]), 1e-12))
            count += 1
        return total / max(1, count)

    def perplexity(self, token_ids: Sequence[int]) -> float:
        return math.exp(self.negative_log_likelihood(token_ids))

    def to_dict(self) -> dict[str, Any]:
        return {"order": self.order, "vocab_size": self.vocab_size, "alpha": self.alpha, "counts": self.counts, "context_totals": self.context_totals}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NGramLanguageModel":
        return cls(int(payload["order"]), int(payload["vocab_size"]), dict(payload.get("counts") or {}), dict(payload.get("context_totals") or {}), float(payload.get("alpha", 0.1)))


@dataclass
class LanguageModelBundle:
    tokenizer: BPETokenizer
    model: NGramLanguageModel | ProductionTransformerRuntime
    backend: str = "ngram"
    metadata: dict[str, Any] = field(default_factory=dict)

    def encode(self, text: str, **kwargs: Any) -> list[int]:
        return self.tokenizer.encode(text, **kwargs)

    def decode(self, ids: Sequence[int]) -> str:
        return self.tokenizer.decode(ids)

    def generate(self, prompt: str, steps: int = 32, *, temperature: float = 1.0, seed: int | None = None) -> str:
        prompt_ids = self.tokenizer.encode(prompt, add_bos=True)
        if isinstance(self.model, NGramLanguageModel):
            ids = self.model.generate(prompt_ids, steps=steps, temperature=temperature, seed=seed)
        else:
            ids = self.model.generate(prompt_ids, steps=steps)
        return self.tokenizer.decode(ids)

    def perplexity(self, texts: Sequence[str]) -> float | None:
        if not isinstance(self.model, NGramLanguageModel):
            return None
        ids: list[int] = []
        for text in texts:
            ids.extend(self.tokenizer.encode(text, add_bos=True, add_eos=True))
        return self.model.perplexity(ids)

    def to_dict(self) -> dict[str, Any]:
        if isinstance(self.model, NGramLanguageModel):
            model_payload = {"type": "ngram", "payload": self.model.to_dict()}
        else:
            model_payload = {"type": "transformer-runtime", "payload": self.model.to_dict()}
        return {"format": LANGUAGE_MODEL_FORMAT, "backend": self.backend, "tokenizer": self.tokenizer.to_dict(), "model": model_payload, "metadata": self.metadata}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LanguageModelBundle":
        if payload.get("format") not in {LANGUAGE_MODEL_FORMAT, None}:
            raise ValueError(f"unsupported language model format: {payload.get('format')}")
        tokenizer = BPETokenizer.from_dict(payload["tokenizer"])
        model_type = payload["model"]["type"]
        if model_type == "ngram":
            model: NGramLanguageModel | ProductionTransformerRuntime = NGramLanguageModel.from_dict(payload["model"]["payload"])
        elif model_type == "transformer-runtime":
            model = ProductionTransformerRuntime.from_dict(payload["model"]["payload"])
        else:
            raise ValueError(f"unsupported language model backend: {model_type}")
        return cls(tokenizer=tokenizer, model=model, backend=str(payload.get("backend", model_type)), metadata=dict(payload.get("metadata") or {}))

    def save(self, path: str | Path) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
        return str(p)

    @classmethod
    def load(cls, path: str | Path) -> "LanguageModelBundle":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def summary(self) -> dict[str, Any]:
        return {"format": LANGUAGE_MODEL_FORMAT, "backend": self.backend, "tokenizer": self.tokenizer.summary(), "metadata": self.metadata}


def train_ngram_lm(
    texts: Sequence[str],
    *,
    merges: int = 200,
    order: int = 3,
    alpha: float = 0.1,
    lowercase: bool = False,
) -> LanguageModelBundle:
    tokenizer = BPETokenizer.train(texts, merges=merges, lowercase=lowercase)
    model = NGramLanguageModel(order=order, vocab_size=max(1, len(tokenizer.vocab)), alpha=alpha)
    for text in texts:
        model.train_sequence(tokenizer.encode(text, add_bos=True, add_eos=True))
    return LanguageModelBundle(tokenizer=tokenizer, model=model, backend="ngram", metadata={"texts": len(texts), "order": order, "alpha": alpha})


def create_transformer_lm(vocab_size: int, **kwargs: Any) -> ProductionTransformerRuntime:
    return ProductionTransformerRuntime(TransformerConfig(vocab_size=vocab_size, **kwargs))


def train_tiny_lm(texts: Sequence[str], merges: int = 20, epochs: int = 3, learning_rate: float = 0.1) -> dict[str, Any]:
    """Backward-compatible API returning tokenizer/model/history.

    The implementation now trains the original TinyLanguageModel for compatibility
    while new production callers should use train_ngram_lm().
    """
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


def load_language_model(path: str | Path) -> LanguageModelBundle:
    return LanguageModelBundle.load(path)


__all__ = [
    "LANGUAGE_MODEL_FORMAT",
    "TinyLanguageModel",
    "NGramLanguageModel",
    "LanguageModelBundle",
    "train_ngram_lm",
    "create_transformer_lm",
    "train_tiny_lm",
    "load_tiny_lm",
    "load_language_model",
]
