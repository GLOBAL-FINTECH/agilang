"""Byte-pair encoding tokenizer starter for AGILANG."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Sequence


def _word_symbols(word: str) -> tuple[str, ...]:
    return tuple(word) + ("</w>",)


@dataclass
class BPETokenizer:
    merges: list[tuple[str, str]] = field(default_factory=list)
    vocab: dict[str, int] = field(default_factory=dict)

    @classmethod
    def train(cls, texts: Sequence[str], merges: int = 50) -> "BPETokenizer":
        words: Counter[tuple[str, ...]] = Counter()
        for text in texts:
            for word in text.split():
                words[_word_symbols(word)] += 1
        learned: list[tuple[str, str]] = []
        for _ in range(max(0, merges)):
            pairs: Counter[tuple[str, str]] = Counter()
            for symbols, count in words.items():
                for i in range(len(symbols) - 1):
                    pairs[(symbols[i], symbols[i + 1])] += count
            if not pairs:
                break
            best = pairs.most_common(1)[0][0]
            learned.append(best)
            new_words: Counter[tuple[str, ...]] = Counter()
            bigram = "".join(best)
            for symbols, count in words.items():
                out = []
                i = 0
                while i < len(symbols):
                    if i < len(symbols) - 1 and (symbols[i], symbols[i + 1]) == best:
                        out.append(bigram)
                        i += 2
                    else:
                        out.append(symbols[i])
                        i += 1
                new_words[tuple(out)] += count
            words = new_words
        tokens = ["<pad>", "<unk>"] + sorted({s for word in words for s in word})
        return cls(learned, {tok: idx for idx, tok in enumerate(tokens)})

    def encode_word(self, word: str) -> list[str]:
        symbols = list(_word_symbols(word))
        for pair in self.merges:
            merged = "".join(pair)
            out = []
            i = 0
            while i < len(symbols):
                if i < len(symbols) - 1 and (symbols[i], symbols[i + 1]) == pair:
                    out.append(merged)
                    i += 2
                else:
                    out.append(symbols[i])
                    i += 1
            symbols = out
        return symbols

    def encode(self, text: str) -> list[int]:
        ids: list[int] = []
        unk = self.vocab.get("<unk>", 1)
        for word in text.split():
            ids.extend(self.vocab.get(tok, unk) for tok in self.encode_word(word))
        return ids

    def summary(self) -> dict[str, int]:
        return {"merges": len(self.merges), "vocab_size": len(self.vocab)}


__all__ = ["BPETokenizer"]
