"""Indexed AGIRecord v2 dataset format.

This keeps JSONL portability while adding an index sidecar for random access.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .agirecord import AGIRecord


@dataclass
class IndexedAGIRecord:
    data_path: Path
    index_path: Path
    offsets: list[int]

    @classmethod
    def write(cls, data_path: str | Path, records: Sequence[AGIRecord]) -> "IndexedAGIRecord":
        path = Path(data_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        index_path = path.with_suffix(path.suffix + ".index")
        offsets: list[int] = []
        pos = 0
        with path.open("wb") as fh:
            for record in records:
                offsets.append(pos)
                line = (record.to_json() + "\n").encode("utf-8")
                fh.write(line)
                pos += len(line)
        index_path.write_text(json.dumps({"format": "agirecord-index-v2", "offsets": offsets}, indent=2), encoding="utf-8")
        return cls(path, index_path, offsets)

    @classmethod
    def open(cls, data_path: str | Path) -> "IndexedAGIRecord":
        path = Path(data_path)
        index_path = path.with_suffix(path.suffix + ".index")
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        return cls(path, index_path, [int(v) for v in payload.get("offsets", [])])

    def __len__(self) -> int:
        return len(self.offsets)

    def get(self, index: int) -> AGIRecord:
        offset = self.offsets[index]
        with self.data_path.open("rb") as fh:
            fh.seek(offset)
            return AGIRecord.from_json(fh.readline().decode("utf-8"))

    def summary(self) -> dict[str, Any]:
        return {"format": "agirecord-index-v2", "records": len(self), "data": str(self.data_path), "index": str(self.index_path)}


__all__ = ["IndexedAGIRecord"]
