"""AGIRecord dataset engine for AGILANG AIFlow.

AGIRecord is a simple JSONL-based native training record format for AGILANG.
It is designed for correctness and portability first. A binary indexed format
can be added later for large-scale training.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence


@dataclass
class AGIRecord:
    features: Any
    label: Any
    metadata: dict[str, Any] | None = None

    def to_json(self) -> str:
        return json.dumps({"features": self.features, "label": self.label, "metadata": self.metadata or {}}, separators=(",", ":"))

    @classmethod
    def from_json(cls, line: str) -> "AGIRecord":
        data = json.loads(line)
        return cls(data.get("features"), data.get("label"), data.get("metadata") or {})


class AGIRecordDataset:
    def __init__(self, records: Sequence[AGIRecord]) -> None:
        self.records = list(records)

    @classmethod
    def from_pairs(cls, features: Sequence[Any], labels: Sequence[Any]) -> "AGIRecordDataset":
        return cls([AGIRecord(x, y) for x, y in zip(features, labels)])

    @classmethod
    def load(cls, path: str | Path) -> "AGIRecordDataset":
        rows = []
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(str(path))
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(AGIRecord.from_json(line))
        return cls(rows)

    def save(self, path: str | Path) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(record.to_json() for record in self.records) + ("\n" if self.records else ""), encoding="utf-8")
        return str(p)

    def shuffle(self, seed: int = 42) -> "AGIRecordDataset":
        rows = list(self.records)
        random.Random(seed).shuffle(rows)
        return AGIRecordDataset(rows)

    def map(self, fn: Callable[[AGIRecord], AGIRecord]) -> "AGIRecordDataset":
        return AGIRecordDataset([fn(record) for record in self.records])

    def batch(self, size: int) -> list[list[AGIRecord]]:
        if size <= 0:
            raise ValueError("batch size must be positive")
        return [self.records[i:i + size] for i in range(0, len(self.records), size)]

    def split(self, test_ratio: float = 0.2) -> dict[str, "AGIRecordDataset"]:
        cut = int(len(self.records) * (1.0 - test_ratio))
        return {"train": AGIRecordDataset(self.records[:cut]), "test": AGIRecordDataset(self.records[cut:])}

    def summary(self) -> dict[str, Any]:
        return {"format": "agirecord-jsonl", "records": len(self.records), "has_metadata": any(bool(r.metadata) for r in self.records)}


def write_agirecord(path: str | Path, features: Sequence[Any], labels: Sequence[Any]) -> str:
    return AGIRecordDataset.from_pairs(features, labels).save(path)


def read_agirecord(path: str | Path) -> AGIRecordDataset:
    return AGIRecordDataset.load(path)


__all__ = ["AGIRecord", "AGIRecordDataset", "write_agirecord", "read_agirecord"]
