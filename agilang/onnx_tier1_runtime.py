"""ONNX execution bridge for AGILANG AIFlow.

The descriptor executor remains dependency-free for small graphs and tests. The
production path now uses optional `onnxruntime` when it is installed, giving
AGILANG a real route for executing actual `.onnx` model files without pretending
that the descriptor executor is a full ONNX parser.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import math
from pathlib import Path
from typing import Any, Sequence

ONNX_RUNTIME_FORMAT = "agilang-onnx-runtime-v2"


class ONNXRuntimeUnavailable(RuntimeError):
    """Raised when production ONNX execution is requested without onnxruntime."""


def onnxruntime_available() -> bool:
    return importlib.util.find_spec("onnxruntime") is not None


def onnx_available() -> bool:
    return importlib.util.find_spec("onnx") is not None


# ---------------------------------------------------------------------------
# Dependency-free descriptor executor
# ---------------------------------------------------------------------------

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
        if rows * cols > len(values):
            raise ValueError("Reshape target is larger than flattened input")
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
    raise NotImplementedError(f"ONNX descriptor op not implemented: {op_type}")


def execute_graph(nodes: Sequence[dict[str, Any]], inputs: dict[str, Any]) -> dict[str, Any]:
    env = dict(inputs)
    for node in nodes:
        op_inputs = [env[name] if isinstance(name, str) else name for name in node.get("inputs", [])]
        env[node["output"]] = execute_node(node["op_type"], op_inputs, node.get("attrs") or {})
    return env


# ---------------------------------------------------------------------------
# Production ONNX Runtime bridge
# ---------------------------------------------------------------------------

@dataclass
class ONNXInputSpec:
    name: str
    shape: Any
    type: str


@dataclass
class ONNXOutputSpec:
    name: str
    shape: Any
    type: str


class ONNXModel:
    """Thin production wrapper around optional onnxruntime.InferenceSession."""

    def __init__(self, path: str | Path, *, providers: Sequence[str] | None = None, session_options: Any = None) -> None:
        if not onnxruntime_available():
            raise ONNXRuntimeUnavailable("onnxruntime is not installed. Install `onnxruntime` or `onnxruntime-gpu` to execute real .onnx model files.")
        import onnxruntime as ort  # type: ignore

        self.path = str(Path(path))
        provider_list = list(providers or ort.get_available_providers())
        self.session = ort.InferenceSession(self.path, sess_options=session_options, providers=provider_list)
        self.providers = self.session.get_providers()

    @property
    def inputs(self) -> list[ONNXInputSpec]:
        return [ONNXInputSpec(i.name, i.shape, i.type) for i in self.session.get_inputs()]

    @property
    def outputs(self) -> list[ONNXOutputSpec]:
        return [ONNXOutputSpec(o.name, o.shape, o.type) for o in self.session.get_outputs()]

    def predict(self, inputs: dict[str, Any], *, output_names: Sequence[str] | None = None) -> dict[str, Any]:
        names = list(output_names or [o.name for o in self.session.get_outputs()])
        result = self.session.run(names, inputs)
        return {name: value for name, value in zip(names, result)}

    def summary(self) -> dict[str, Any]:
        return {
            "format": ONNX_RUNTIME_FORMAT,
            "backend": "onnxruntime",
            "path": self.path,
            "providers": self.providers,
            "inputs": [spec.__dict__ for spec in self.inputs],
            "outputs": [spec.__dict__ for spec in self.outputs],
        }


def load_onnx_model(path: str | Path, *, providers: Sequence[str] | None = None, session_options: Any = None) -> ONNXModel:
    return ONNXModel(path, providers=providers, session_options=session_options)


def onnx_runtime_status() -> dict[str, Any]:
    payload = {"format": ONNX_RUNTIME_FORMAT, "onnx_available": onnx_available(), "onnxruntime_available": onnxruntime_available(), "descriptor_runtime": True}
    if onnxruntime_available():
        import onnxruntime as ort  # type: ignore
        payload["providers"] = ort.get_available_providers()
    else:
        payload["providers"] = []
    return payload


def require_onnxruntime() -> None:
    if not onnxruntime_available():
        raise ONNXRuntimeUnavailable("Production ONNX execution requires `onnxruntime` or `onnxruntime-gpu`.")


__all__ = [
    "ONNX_RUNTIME_FORMAT",
    "ONNXRuntimeUnavailable",
    "onnxruntime_available",
    "onnx_available",
    "onnx_runtime_status",
    "require_onnxruntime",
    "ONNXModel",
    "ONNXInputSpec",
    "ONNXOutputSpec",
    "load_onnx_model",
    "execute_node",
    "execute_graph",
    "relu",
    "sigmoid",
    "softmax",
    "matmul",
    "add",
    "mul",
    "flatten",
    "reshape",
    "transpose",
    "gemm",
]
