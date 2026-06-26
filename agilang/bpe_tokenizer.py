"""Production-facing byte-pair encoding tokenizer for AGILANG AIFlow.

The first tokenizer shipped as a training/encode starter. This version keeps the
same lightweight dependency-free design, but adds the missing pieces needed for
real application use: deterministic special-token handling, decode support,
JSON persistence, validation, and stable metadata.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Sequence

TOKENIZER_FORMAT = "agilang-bpe-tokenizer-v2"
DEFAULT_SPECIAL_TOKENS = ["<pad>", "<unk>", "<bos>", "<eos>"]


def _word_symbols(word: str) -> tuple[str, ...]:
    return tuple(word) + ("</w>",)


def _merge_symbols(symbols: Sequence[str], pair: tuple[str, str]) -> list[str]:
    merged = "".join(pair)
    out: list[str] = []
    i = 0
    while i < len(symbols):
        if i < len(symbols) - 1 and (symbols[i], symbols[i + 1]) == pair:
            out.append(merged)
            i += 2
        else:
            out.append(symbols[i])
            i += 1
    return out


@dataclass
class BPETokenizer:
    merges: list[tuple[str, str]] = field(default_factory=list)
    vocab: dict[str, int] = field(default_factory=dict)
    special_tokens: list[str] = field(default_factory=lambda: list(DEFAULT_SPECIAL_TOKENS))
    lowercase: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    id_to_token: dict[int, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.merges = [tuple(pair) for pair in self.merges]
        self.vocab = {str(k): int(v) for k, v in self.vocab.items()}
        if not self.id_to_token:
            self.id_to_token = {idx: tok for tok, idx in self.vocab.items()}
        else:
            self.id_to_token = {int(k): str(v) for k, v in self.id_to_token.items()}
        for token in self.special_tokens:
            if token not in self.vocab:
                self.vocab[token] = len(self.vocab)
                self.id_to_token[self.vocab[token]] = token

    @classmethod
    def train(
        cls,
        texts: Sequence[str],
        merges: int = 50,
        *,
        special_tokens: Sequence[str] | None = None,
        lowercase: bool = False,
        min_frequency: int = 1,
    ) -> "BPETokenizer":
        """Train a deterministic BPE tokenizer from text.

        This is still a compact tokenizer, not a byte-level SentencePiece clone.
        It is designed to be portable inside AGILANG projects and good enough for
        small/medium domain corpora.
        """
        special = list(special_tokens or DEFAULT_SPECIAL_TOKENS)
        words: Counter[tuple[str, ...]] = Counter()
        for text in texts:
            source = text.lower() if lowercase else text
            for word in source.split():
                words[_word_symbols(word)] += 1
        if min_frequency > 1:
            words = Counter({word: count for word, count in words.items() if count >= min_frequency})
        learned: list[tuple[str, str]] = []
        for _ in range(max(0, int(merges))):
            pairs: Counter[tuple[str, str]] = Counter()
            for symbols, count in words.items():
                for i in range(len(symbols) - 1):
                    pairs[(symbols[i], symbols[i + 1])] += count
            if not pairs:
                break
            best, freq = pairs.most_common(1)[0]
            if freq < max(1, min_frequency):
                break
            learned.append(best)
            new_words: Counter[tuple[str, ...]] = Counter()
            for symbols, count in words.items():
                new_words[tuple(_merge_symbols(symbols, best))] += count
            words = new_words
        learned_symbols = sorted({symbol for word in words for symbol in word})
        vocab_tokens = []
        for token in special + learned_symbols:
            if token not in vocab_tokens:
                vocab_tokens.append(token)
        tokenizer = cls(
            merges=learned,
            vocab={tok: idx for idx, tok in enumerate(vocab_tokens)},
            special_tokens=special,
            lowercase=lowercase,
            metadata={"trained_texts": len(texts), "requested_merges": int(merges), "min_frequency": int(min_frequency)},
        )
        return tokenizer

    @property
    def unk_id(self) -> int:
        return self.vocab.get("<unk>", 1)

    @property
    def bos_id(self) -> int | None:
        return self.vocab.get("<bos>")

    @property
    def eos_id(self) -> int | None:
        return self.vocab.get("<eos>")

    def encode_word(self, word: str) -> list[str]:
        source = word.lower() if self.lowercase else word
        symbols = list(_word_symbols(source))
        for pair in self.merges:
            symbols = _merge_symbols(symbols, pair)
        return symbols

    def encode(
        self,
        text: str,
        *,
        add_bos: bool = False,
        add_eos: bool = False,
        max_length: int | None = None,
    ) -> list[int]:
        ids: list[int] = []
        if add_bos and self.bos_id is not None:
            ids.append(self.bos_id)
        for word in text.split():
            ids.extend(self.vocab.get(tok, self.unk_id) for tok in self.encode_word(word))
        if add_eos and self.eos_id is not None:
            ids.append(self.eos_id)
        if max_length is not None:
            ids = ids[: max(0, int(max_length))]
        return ids

    def decode(self, ids: Sequence[int], *, skip_special: bool = True) -> str:
        """Decode token IDs back into approximate text.

        BPE tokenization is lossy for unknown tokens, but trained tokens round-trip
        cleanly for whitespace-separated corpora.
        """
        words: list[str] = []
        current = ""
        special = set(self.special_tokens)
        for token_id in ids:
            token = self.id_to_token.get(int(token_id), "<unk>")
            if skip_special and token in special:
                continue
            if token.endswith("</w>"):
                current += token[:-4]
                words.append(current)
                current = ""
            elif token == "</w>":
                words.append(current)
                current = ""
            elif token in special:
                if current:
                    words.append(current)
                    current = ""
                words.append(token)
            else:
                current += token
        if current:
            words.append(current)
        return " ".join(word for word in words if word != "")

    def token(self, token_id: int) -> str:
        return self.id_to_token.get(int(token_id), "<unk>")

    def token_id(self, token: str) -> int:
        return self.vocab.get(token, self.unk_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": TOKENIZER_FORMAT,
            "merges": [list(pair) for pair in self.merges],
            "vocab": self.vocab,
            "special_tokens": self.special_tokens,
            "lowercase": self.lowercase,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BPETokenizer":
        if payload.get("format") not in {None, TOKENIZER_FORMAT, "agilang-bpe-tokenizer-v1"}:
            raise ValueError(f"unsupported tokenizer format: {payload.get('format')}")
        return cls(
            merges=[tuple(pair) for pair in payload.get("merges", [])],
            vocab={str(k): int(v) for k, v in payload.get("vocab", {}).items()},
            special_tokens=list(payload.get("special_tokens") or DEFAULT_SPECIAL_TOKENS),
            lowercase=bool(payload.get("lowercase", False)),
            metadata=dict(payload.get("metadata") or {}),
        )

    def save(self, path: str | Path) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return str(p)

    @classmethod
    def load(cls, path: str | Path) -> "BPETokenizer":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def summary(self) -> dict[str, Any]:
        return {
            "format": TOKENIZER_FORMAT,
            "merges": len(self.merges),
            "vocab_size": len(self.vocab),
            "special_tokens": list(self.special_tokens),
            "lowercase": self.lowercase,
        }


def train_bpe_tokenizer(texts: Sequence[str], merges: int = 50, **kwargs: Any) -> BPETokenizer:
    return BPETokenizer.train(texts, merges=merges, **kwargs)


def load_bpe_tokenizer(path: str | Path) -> BPETokenizer:
    return BPETokenizer.load(path)


__all__ = ["BPETokenizer", "train_bpe_tokenizer", "load_bpe_tokenizer", "TOKENIZER_FORMAT", "DEFAULT_SPECIAL_TOKENS"]
