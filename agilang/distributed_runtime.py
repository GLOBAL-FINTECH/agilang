"""Distributed training reference executor for AGILANG AIFlow.

This is a local reference implementation of gradient averaging and worker-step
planning. Real multi-node transport can later replace this interface.
"""
from __future__ import annotations

from typing import Sequence


def allreduce_average(vectors: Sequence[Sequence[float]]) -> list[float]:
    if not vectors:
        return []
    width = len(vectors[0])
    if any(len(v) != width for v in vectors):
        raise ValueError("allreduce vectors must have equal length")
    return [sum(float(v[i]) for v in vectors) / len(vectors) for i in range(width)]


def shard_indices(total: int, workers: int) -> list[list[int]]:
    workers = max(1, int(workers))
    shards = [[] for _ in range(workers)]
    for idx in range(total):
        shards[idx % workers].append(idx)
    return shards


def distributed_step_plan(samples: int, workers: int) -> dict[str, object]:
    shards = shard_indices(samples, workers)
    return {"samples": samples, "workers": workers, "shards": shards, "sync": "allreduce_average"}


__all__ = ["allreduce_average", "shard_indices", "distributed_step_plan"]
