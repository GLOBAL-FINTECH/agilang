"""AGILANG native ND tensor and reverse-mode autodiff engine.

This is the next core layer toward an AGILANG-native tensor runtime. It implements
a scalar/list-backed tensor engine with reverse-mode autodiff for common training
operations. The design is intentionally simple and auditable before native
C/WASM/GPU kernels are expanded.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence


def _infer_shape(data: Any) -> tuple[int, ...]:
    if isinstance(data, NDTensor):
        return data.shape
    if isinstance(data, (int, float)):
        return ()
    if isinstance(data, list):
        if not data:
            return (0,)
        child = _infer_shape(data[0])
        for item in data:
            if _infer_shape(item) != child:
                raise ValueError("ragged tensors are not supported")
        return (len(data),) + child
    raise TypeError(f"unsupported tensor data: {type(data).__name__}")


def _flatten_values(data: Any) -> list[float]:
    if isinstance(data, NDTensor):
        return list(data.data)
    if isinstance(data, (int, float)):
        return [float(data)]
    if isinstance(data, list):
        out: list[float] = []
        for item in data:
            out.extend(_flatten_values(item))
        return out
    raise TypeError(f"unsupported tensor data: {type(data).__name__}")


def _flatten(data: Any) -> tuple[list[float], tuple[int, ...]]:
    if isinstance(data, NDTensor):
        return list(data.data), data.shape
    shape = _infer_shape(data)
    return _flatten_values(data), shape


def _numel(shape: tuple[int, ...]) -> int:
    if shape == ():
        return 1
    total = 1
    for dim in shape:
        total *= int(dim)
    return total


def _unflatten(flat: Sequence[float], shape: tuple[int, ...]) -> Any:
    values = [float(v) for v in flat]
    if shape == ():
        return values[0] if values else 0.0
    if not shape:
        return values[0] if values else 0.0

    def build(offset: int, dims: tuple[int, ...]) -> tuple[Any, int]:
        if not dims:
            return (values[offset] if offset < len(values) else 0.0), offset + 1
        size = int(dims[0])
        row = []
        current = offset
        for _ in range(size):
            item, current = build(current, dims[1:])
            row.append(item)
        return row, current

    result, _ = build(0, shape)
    return result


def _same_shape(a: "NDTensor", b: "NDTensor") -> None:
    if a.shape != b.shape:
        raise ValueError(f"shape mismatch: {a.shape} != {b.shape}")


@dataclass(eq=False)
class NDTensor:
    data: list[float]
    shape: tuple[int, ...]
    requires_grad: bool = False
    grad: list[float] | None = None
    parents: list["NDTensor"] = field(default_factory=list)
    backward_fn: Callable[[list[float]], None] | None = None
    name: str | None = None

    def __post_init__(self) -> None:
        expected = _numel(self.shape)
        if expected != len(self.data):
            raise ValueError(f"data length {len(self.data)} does not match shape {self.shape}")
        if self.requires_grad and self.grad is None:
            self.grad = [0.0 for _ in self.data]

    def tolist(self) -> Any:
        return _unflatten(self.data, self.shape)

    def item(self) -> float:
        if len(self.data) != 1:
            raise ValueError("item() requires a scalar tensor")
        return float(self.data[0])

    def zero_grad(self) -> None:
        self.grad = [0.0 for _ in self.data]

    def _accumulate_grad(self, incoming: Sequence[float]) -> None:
        if not self.requires_grad:
            return
        if self.grad is None:
            self.grad = [0.0 for _ in self.data]
        for i, value in enumerate(incoming):
            self.grad[i] += float(value)

    def _topo(self, visited: set[int], out: list["NDTensor"]) -> None:
        if id(self) in visited:
            return
        visited.add(id(self))
        for parent in self.parents:
            parent._topo(visited, out)
        out.append(self)

    def backward(self, grad: Sequence[float] | None = None) -> None:
        if grad is None:
            if len(self.data) != 1:
                raise ValueError("non-scalar backward requires explicit gradient")
            grad = [1.0]
        order: list[NDTensor] = []
        self._topo(set(), order)
        self._accumulate_grad(list(grad))
        for node in reversed(order):
            if node.backward_fn is not None and node.grad is not None:
                node.backward_fn(node.grad)

    def __add__(self, other: Any) -> "NDTensor":
        other = ndtensor(other)
        if other.shape == ():
            out_data = [v + other.data[0] for v in self.data]
            out_shape = self.shape
        else:
            _same_shape(self, other)
            out_data = [a + b for a, b in zip(self.data, other.data)]
            out_shape = self.shape
        out = NDTensor(out_data, out_shape, self.requires_grad or other.requires_grad, parents=[self, other])
        def back(g: list[float]) -> None:
            self._accumulate_grad(g)
            if other.shape == ():
                other._accumulate_grad([sum(g)])
            else:
                other._accumulate_grad(g)
        out.backward_fn = back
        return out

    def __sub__(self, other: Any) -> "NDTensor":
        return self + (ndtensor(other) * -1.0)

    def __mul__(self, other: Any) -> "NDTensor":
        other = ndtensor(other)
        if other.shape == ():
            out_data = [v * other.data[0] for v in self.data]
            out_shape = self.shape
        else:
            _same_shape(self, other)
            out_data = [a * b for a, b in zip(self.data, other.data)]
            out_shape = self.shape
        out = NDTensor(out_data, out_shape, self.requires_grad or other.requires_grad, parents=[self, other])
        def back(g: list[float]) -> None:
            if other.shape == ():
                self._accumulate_grad([gv * other.data[0] for gv in g])
                other._accumulate_grad([sum(gv * sv for gv, sv in zip(g, self.data))])
            else:
                self._accumulate_grad([gv * ov for gv, ov in zip(g, other.data)])
                other._accumulate_grad([gv * sv for gv, sv in zip(g, self.data)])
        out.backward_fn = back
        return out

    def __pow__(self, power: float) -> "NDTensor":
        out_data = [v ** power for v in self.data]
        out = NDTensor(out_data, self.shape, self.requires_grad, parents=[self])
        def back(g: list[float]) -> None:
            self._accumulate_grad([gv * power * (v ** (power - 1)) for gv, v in zip(g, self.data)])
        out.backward_fn = back
        return out

    def sum(self) -> "NDTensor":
        out = NDTensor([sum(self.data)], (), self.requires_grad, parents=[self])
        def back(g: list[float]) -> None:
            self._accumulate_grad([g[0] for _ in self.data])
        out.backward_fn = back
        return out

    def mean(self) -> "NDTensor":
        return self.sum() * (1.0 / max(1, len(self.data)))

    def relu(self) -> "NDTensor":
        out = NDTensor([max(0.0, v) for v in self.data], self.shape, self.requires_grad, parents=[self])
        def back(g: list[float]) -> None:
            self._accumulate_grad([gv if v > 0 else 0.0 for gv, v in zip(g, self.data)])
        out.backward_fn = back
        return out

    def sigmoid(self) -> "NDTensor":
        vals = [1.0 / (1.0 + math.exp(-v)) for v in self.data]
        out = NDTensor(vals, self.shape, self.requires_grad, parents=[self])
        def back(g: list[float]) -> None:
            self._accumulate_grad([gv * y * (1.0 - y) for gv, y in zip(g, vals)])
        out.backward_fn = back
        return out


def ndtensor(data: Any, *, requires_grad: bool = False, name: str | None = None) -> NDTensor:
    if isinstance(data, NDTensor):
        return data
    flat, shape = _flatten(data)
    return NDTensor(flat, shape, requires_grad=requires_grad, name=name)


def variable(data: Any, name: str | None = None) -> NDTensor:
    return ndtensor(data, requires_grad=True, name=name)


def matmul(a: Any, b: Any) -> NDTensor:
    a = ndtensor(a)
    b = ndtensor(b)
    if len(a.shape) != 2 or len(b.shape) != 2:
        raise ValueError("matmul requires rank-2 tensors")
    m, n = a.shape
    n2, p = b.shape
    if n != n2:
        raise ValueError(f"matmul shape mismatch: {a.shape} x {b.shape}")
    out_data = []
    for i in range(m):
        for j in range(p):
            out_data.append(sum(a.data[i * n + k] * b.data[k * p + j] for k in range(n)))
    out = NDTensor(out_data, (m, p), a.requires_grad or b.requires_grad, parents=[a, b])
    def back(g: list[float]) -> None:
        grad_a = [0.0 for _ in a.data]
        grad_b = [0.0 for _ in b.data]
        for i in range(m):
            for j in range(p):
                gv = g[i * p + j]
                for k in range(n):
                    grad_a[i * n + k] += gv * b.data[k * p + j]
                    grad_b[k * p + j] += gv * a.data[i * n + k]
        a._accumulate_grad(grad_a)
        b._accumulate_grad(grad_b)
    out.backward_fn = back
    return out


def mse(y_pred: Any, y_true: Any) -> NDTensor:
    return ((ndtensor(y_pred) - ndtensor(y_true)) ** 2).mean()


def softmax(values: Any) -> list[float]:
    t = ndtensor(values)
    m = max(t.data) if t.data else 0.0
    exps = [math.exp(v - m) for v in t.data]
    total = sum(exps) or 1.0
    return [v / total for v in exps]


def sgd_step(parameters: Sequence[NDTensor], learning_rate: float = 0.01) -> None:
    for p in parameters:
        if p.grad is None:
            continue
        for i, grad in enumerate(p.grad):
            p.data[i] -= learning_rate * grad
        p.zero_grad()


__all__ = ["NDTensor", "ndtensor", "variable", "matmul", "mse", "softmax", "sgd_step"]
