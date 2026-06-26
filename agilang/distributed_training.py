"""Distributed training planner for AGILANG AIFlow."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TrainingNode:
    name: str
    host: str
    role: str = "worker"
    gpus: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "host": self.host, "role": self.role, "gpus": self.gpus}


def distributed_plan(nodes: list[TrainingNode], strategy: str = "data_parallel") -> dict[str, Any]:
    return {
        "strategy": strategy,
        "nodes": [node.as_dict() for node in nodes],
        "total_gpus": sum(node.gpus for node in nodes),
        "status": "planner_ready_execution_pending",
        "supported_future_modes": ["data_parallel", "tensor_parallel", "pipeline_parallel", "zero_optimizer"],
    }


__all__ = ["TrainingNode", "distributed_plan"]
