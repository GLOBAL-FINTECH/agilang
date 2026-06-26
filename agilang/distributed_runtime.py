"""Distributed training runtime primitives for AGILANG AIFlow.

The original implementation only provided local averaging and a planning helper.
This version adds a production-facing runtime contract with validation and a
shared-filesystem coordinator that can synchronize independent workers on a
single host or cluster with a mounted volume. It is intentionally simple and
inspectable; high-throughput clusters should bridge to NCCL, MPI, Ray, Torch
Distributed, or another audited backend.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import time
from typing import Any, Sequence

DISTRIBUTED_RUNTIME_FORMAT = "agilang-distributed-runtime-v2"


class DistributedRuntimeError(RuntimeError):
    pass


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
    for idx in range(max(0, int(total))):
        shards[idx % workers].append(idx)
    return shards


def distributed_step_plan(samples: int, workers: int) -> dict[str, object]:
    shards = shard_indices(samples, workers)
    return {"samples": samples, "workers": workers, "shards": shards, "sync": "allreduce_average"}


@dataclass(frozen=True)
class WorkerSpec:
    worker_id: int
    workers: int
    run_id: str = "default"

    def __post_init__(self) -> None:
        if self.workers <= 0:
            raise ValueError("workers must be positive")
        if self.worker_id < 0 or self.worker_id >= self.workers:
            raise ValueError("worker_id must be between 0 and workers-1")


@dataclass
class DistributedConfig:
    backend: str = "local"
    workers: int = 1
    run_dir: str = ".agilang/distributed"
    timeout_seconds: float = 30.0
    poll_seconds: float = 0.1
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "format": DISTRIBUTED_RUNTIME_FORMAT,
            "backend": self.backend,
            "workers": self.workers,
            "run_dir": self.run_dir,
            "timeout_seconds": self.timeout_seconds,
            "poll_seconds": self.poll_seconds,
            "metadata": self.metadata,
        }


class FileSystemAllReduceCoordinator:
    """Shared-directory allreduce coordinator for small production deployments.

    Every worker writes a vector file for a named step. Once all workers have
    written, any worker can compute and write the averaged result. This is slower
    than NCCL/MPI but reliable, inspectable, and usable where shared storage is
    available.
    """

    def __init__(self, root: str | Path, worker: WorkerSpec, *, timeout_seconds: float = 30.0, poll_seconds: float = 0.1) -> None:
        self.root = Path(root)
        self.worker = worker
        self.timeout_seconds = float(timeout_seconds)
        self.poll_seconds = float(poll_seconds)
        self.run_root = self.root / worker.run_id
        self.run_root.mkdir(parents=True, exist_ok=True)

    def _step_dir(self, step: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(step)) or "step"
        path = self.run_root / safe
        path.mkdir(parents=True, exist_ok=True)
        return path

    def allreduce_average(self, step: str, vector: Sequence[float]) -> list[float]:
        step_dir = self._step_dir(step)
        vector = [float(v) for v in vector]
        own = step_dir / f"worker_{self.worker.worker_id}.json"
        own.write_text(json.dumps({"worker_id": self.worker.worker_id, "vector": vector}, separators=(",", ":")) + "\n", encoding="utf-8")
        deadline = time.time() + self.timeout_seconds
        while time.time() <= deadline:
            files = sorted(step_dir.glob("worker_*.json"))
            if len(files) >= self.worker.workers:
                vectors = [json.loads(path.read_text(encoding="utf-8"))["vector"] for path in files[: self.worker.workers]]
                result = allreduce_average(vectors)
                result_path = step_dir / "result.json"
                if not result_path.exists():
                    result_path.write_text(json.dumps({"vector": result}, separators=(",", ":")) + "\n", encoding="utf-8")
                return result
            time.sleep(self.poll_seconds)
        raise DistributedRuntimeError(f"allreduce timed out waiting for {self.worker.workers} workers at {step_dir}")

    def cleanup_step(self, step: str) -> None:
        step_dir = self._step_dir(step)
        for path in step_dir.glob("*.json"):
            path.unlink(missing_ok=True)


class DistributedRuntime:
    def __init__(self, config: DistributedConfig | None = None, worker: WorkerSpec | None = None) -> None:
        self.config = config or DistributedConfig()
        self.worker = worker or WorkerSpec(0, self.config.workers)
        if self.config.backend not in {"local", "filesystem"}:
            raise DistributedRuntimeError(f"unsupported distributed backend: {self.config.backend}")
        self.coordinator = None
        if self.config.backend == "filesystem":
            self.coordinator = FileSystemAllReduceCoordinator(self.config.run_dir, self.worker, timeout_seconds=self.config.timeout_seconds, poll_seconds=self.config.poll_seconds)

    def allreduce_average(self, vector: Sequence[float], *, step: str = "step") -> list[float]:
        if self.config.backend == "local":
            return [float(v) for v in vector]
        assert self.coordinator is not None
        return self.coordinator.allreduce_average(step, vector)

    def shard_for_worker(self, samples: int) -> list[int]:
        return shard_indices(samples, self.worker.workers)[self.worker.worker_id]

    def status(self) -> dict[str, Any]:
        return {"format": DISTRIBUTED_RUNTIME_FORMAT, "config": self.config.as_dict(), "worker": self.worker.__dict__}


def distributed_runtime(config: DistributedConfig | None = None, worker: WorkerSpec | None = None) -> DistributedRuntime:
    return DistributedRuntime(config, worker)


def distributed_capabilities() -> dict[str, Any]:
    return {
        "format": DISTRIBUTED_RUNTIME_FORMAT,
        "backends": {
            "local": {"available": True, "production": True, "notes": "single-worker/no-op allreduce for deployment parity"},
            "filesystem": {"available": True, "production": True, "notes": "shared-directory coordinator for small worker groups"},
            "nccl": {"available": False, "production": False, "notes": "bridge planned through external backend"},
            "mpi": {"available": False, "production": False, "notes": "bridge planned through external backend"},
        },
    }


__all__ = [
    "DISTRIBUTED_RUNTIME_FORMAT",
    "DistributedRuntimeError",
    "WorkerSpec",
    "DistributedConfig",
    "FileSystemAllReduceCoordinator",
    "DistributedRuntime",
    "distributed_runtime",
    "distributed_capabilities",
    "allreduce_average",
    "shard_indices",
    "distributed_step_plan",
]
