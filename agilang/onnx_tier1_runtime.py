"""ONNX Tier 1 reference runtime for AGILANG AIFlow.

This is a dependency-light operator executor for the most common ONNX-style ops.
It is not a full ONNX parser yet; it executes descriptor dictionaries and gives
AGILANG a clear path to load real ONNX graphs later.
"""
from __future__ import annotations

import math
from typing import Any, Sequence


def relu(x: Any) -> Any:
    if isinstance(x, list):
        return [relu(v) for v in x]
    return max(0.0, float(x))


def sigmoid(x: Any) -> Any:
    if isinstance(x, list):
        return [sigmoid(v) for v in x]
    return 1.0 / (1.0 + math.exp(-float(x)))


def softmax(values: Sequence[float]) -> list[float]:
    vals = [float(v) for v in values]
    if not vals:
        return []
    m = max(vals)
    exps = [math.exp(v - m) for v in vals]
    total = sum(exps) or 1.0
    return [v / total for v in exps]


def matmul(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> list[list[float]]:
    if not a or not b:
        return []
    if len(a[0]) != len(b):
        raise ValueError("MatMul shape mismatch")
    return [[sum(float(row[k]) * float(b[k][j]) for k in range(len(b))) for j in range(len(b[0]))] for row in a]


def add(a: Any, b: Any) -> Any:
    if isinstance(a, list) and isinstance(b, list):
        return [add(x, y) for x, y in zip(a, b)]
    if isinstance(a, list):
        return [add(x, b) for x in a]
    if isinstance(b, list):
        return [add(a, y) for y in b]
    return float(a) + float(b)


def mul(a: Any, b: Any) -> Any:
    if isinstance(a, list) and isinstance(b, list):
        return [mul(x, y) for x, y in zip(a, b)]
    if isinstance(a, list):
        return [mul(x, b) for x in a]
    if isinstance(b, list):
        return [mul(a, y) for y in b]
    return float(a) * float(b)


def flatten(x: Any) -> list[float]:
    if isinstance(x, list):
        out: list[float] = []
        for v in x:
            out.extend(flatten(v))
        return out
    return [float(x)]


def reshape(flat_values: Sequence[float], shape: Sequence[int]) -> Any:
    values = [float(v) for v in flat_values]
    if len(shape) == 1:
        return values[: int(shape[0])]
    if len(shape) == 2:
        rows, cols = int(shape[0]), int(shape[1])
        return [[values[i * cols + j] for j in range(cols)] for i in range(rows)]
    raise ValueError("reference reshape supports rank 1 and rank 2")


def transpose(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    return [[float(matrix[i][j]) for i in range(len(matrix))] for j in range(len(matrix[0]))]


def gemm(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]], c: Sequence[Sequence[float]] | None = None) -> list[list[float]]:
    out = matmul(a, b)
    return add(out, c) if c is not None else out


def execute_node(op_type: str, inputs: list[Any], attrs: dict[str, Any] | None = None) -> Any:
    attrs = attrs or {}
    if op_type == "Relu":
        return relu(inputs[0])
    if op_type == "Sigmoid":
        return sigmoid(inputs[0])
    if op_type == "Softmax":
        return softmax(flatten(inputs[0]))
    if op_type == "MatMul":
        return matmul(inputs[0], inputs[1])
    if op_type == "Add":
        return add(inputs[0], inputs[1])
    if op_type == "Mul":
        return mul(inputs[0], inputs[1])
    if op_type == "Flatten":
        return flatten(inputs[0])
    if op_type == "Reshape":
        return reshape(flatten(inputs[0]), attrs.get("shape", inputs[1] if len(inputs) > 1 else []))
    if op_type == "Transpose":
        return transpose(inputs[0])
    if op_type == "Gemm":
        return gemm(inputs[0], inputs[1], inputs[2] if len(inputs) > 2 else None)
    raise NotImplementedError(f"ONNX Tier 1 op not implemented: {op_type}")


def execute_graph(nodes: Sequence[dict[str, Any]], inputs: dict[str, Any]) -> dict[str, Any]:
    env = dict(inputs)
    for node in nodes:
        op_inputs = [env[name] if isinstance(name, str) else name for name in node.get("inputs", [])]
        env[node["output"]] = execute_node(node["op_type"], op_inputs, node.get("attrs") or {})
    return env


__all__ = ["execute_node", "execute_graph", "relu", "sigmoid", "softmax", "matmul", "add", "mul", "flatten", "reshape", "transpose", "gemm"]
