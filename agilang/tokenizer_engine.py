"""Native tokenizer starter engine for AGILANG language and LLM work."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence


@dataclass
class VocabTokenizer:
    token_to_id: dict[str, int]
    unk_token: str = "<unk>"

    @classmethod
    def train_word(cls, texts: Sequence[str], vocab_size: int = 1000) -> "VocabTokenizer":
        counts: Counter[str] = Counter()
        for text in texts:
            counts.update(text.split())
        tokens = ["<pad>", "<unk>", "<bos>", "<eos>"] + [token for token, _ in counts.most_common(max(0, vocab_size - 4))]
        return cls({token: idx for idx, token in enumerate(tokens)})

    def encode(self, text: str, add_special: bool = False) -> list[int]:
        ids = [self.token_to_id.get(token, self.token_to_id.get(self.unk_token, 1)) for token in text.split()]
        if add_special:
            ids = [self.token_to_id.get("<bos>", 2)] + ids + [self.token_to_id.get("<eos>", 3)]
        return ids

    def decode(self, ids: Sequence[int]) -> str:
        reverse = {idx: token for token, idx in self.token_to_id.items()}
        return " ".join(reverse.get(int(idx), self.unk_token) for idx in ids)

    def summary(self) -> dict[str, int]:
        return {"vocab_size": len(self.token_to_id)}


__all__ = ["VocabTokenizer"]
