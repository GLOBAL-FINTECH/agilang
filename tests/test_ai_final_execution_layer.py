from __future__ import annotations

from pathlib import Path

from agilang.distributed_runtime import allreduce_average, distributed_step_plan
from agilang.gpu_kernel_registry import default_registry
from agilang.llm_trainer import train_tiny_lm, load_tiny_lm
from agilang.onnx_tier1_runtime import execute_graph, execute_node, matmul


def test_onnx_tier1_reference_runtime() -> None:
    assert matmul([[1, 2]], [[3], [4]]) == [[11.0]]
    assert execute_node("Relu", [[-1, 2]]) == [0.0, 2.0]
    graph = [
        {"op_type": "MatMul", "inputs": ["x", "w"], "output": "z"},
        {"op_type": "Relu", "inputs": ["z"], "output": "y"},
    ]
    env = execute_graph(graph, {"x": [[1, 2]], "w": [[3], [4]]})
    assert env["y"] == [[11.0]]


def test_tiny_lm_train_save_load(tmp_path: Path) -> None:
    result = train_tiny_lm(["agi trains models", "agi trains apps"], merges=5, epochs=2)
    assert len(result["history"]["loss"]) == 2
    model = result["model"]
    path = tmp_path / "tiny.agi-model"
    model.save(path)
    loaded = load_tiny_lm(path)
    assert loaded.vocab_size == model.vocab_size


def test_distributed_runtime_and_gpu_registry() -> None:
    assert allreduce_average([[1, 3], [3, 5]]) == [2.0, 4.0]
    plan = distributed_step_plan(samples=5, workers=2)
    assert plan["shards"] == [[0, 2, 4], [1, 3]]
    registry = default_registry()
    assert len(registry.available()) >= 20
