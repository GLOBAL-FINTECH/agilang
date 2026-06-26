"""AGILANG Torch-compatible tensor API.

This module provides a PyTorch-style API surface on top of AGILANG's native
NDTensor/autodiff engine and production AI backends. It is intentionally honest:
`torch_compat_status()` reports implemented, delegated and missing areas instead
of claiming exact PyTorch parity.

Goal: make common PyTorch-like workflows portable inside AGILANG while native C,
CUDA and compiler kernels mature.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

from .ndtensor import NDTensor, matmul as _nd_matmul, mse as _nd_mse, ndtensor, sgd_step, softmax as _nd_softmax

TORCH_COMPAT_FORMAT = "agilang-torch-compat-v1"

float32 = "float32"
float64 = "float64"
int64 = "int64"
long = int64


class TorchCompatError(RuntimeError):
    pass


def _unflatten_like(flat: Sequence[float], shape: tuple[int, ...]) -> Any:
    values = [float(v) for v in flat]
    if shape == ():
        return values[0] if values else 0.0

    def build(offset: int, dims: tuple[int, ...]) -> tuple[Any, int]:
        if not dims:
            return (values[offset] if offset < len(values) else 0.0), offset + 1
        out = []
        current = offset
        for _ in range(int(dims[0])):
            item, current = build(current, dims[1:])
            out.append(item)
        return out, current

    result, _ = build(0, shape)
    return result


def _unwrap(value: Any) -> Any:
    return value._tensor if isinstance(value, Tensor) else value


class Tensor:
    """PyTorch-style wrapper around NDTensor.

    Supports common small-model workflows: `.shape`, `.grad`, `.tolist()`,
    `.item()`, `.backward()`, arithmetic, reductions, activations, matmul and
    save/load-compatible state dictionaries.
    """

    def __init__(self, data: Any, *, requires_grad: bool = False, dtype: str = float32, device: str = "cpu", name: str | None = None) -> None:
        if isinstance(data, Tensor):
            self._tensor = data._tensor
            self.dtype = data.dtype
            self.device = data.device
        elif isinstance(data, NDTensor):
            self._tensor = data
            self.dtype = dtype
            self.device = device
        else:
            self._tensor = ndtensor(data, requires_grad=requires_grad, name=name)
            self.dtype = dtype
            self.device = device
        if self.device != "cpu":
            raise TorchCompatError("Native TorchCompat tensors currently execute on AGILANG CPU tensors. Use gpu_kernel_registry for accelerated kernels.")

    @property
    def shape(self) -> tuple[int, ...]:
        return self._tensor.shape

    @property
    def requires_grad(self) -> bool:
        return self._tensor.requires_grad

    @property
    def grad(self) -> Any:
        if self._tensor.grad is None:
            return None
        return _unflatten_like(self._tensor.grad, self.shape)

    @property
    def data(self) -> list[float]:
        return list(self._tensor.data)

    def tolist(self) -> Any:
        return self._tensor.tolist()

    def item(self) -> float:
        return self._tensor.item()

    def zero_grad(self) -> None:
        self._tensor.zero_grad()

    def backward(self, gradient: Any | None = None) -> None:
        if gradient is None:
            self._tensor.backward()
        else:
            self._tensor.backward(ndtensor(gradient).data)

    def mean(self) -> "Tensor":
        return Tensor(self._tensor.mean(), dtype=self.dtype)

    def sum(self) -> "Tensor":
        return Tensor(self._tensor.sum(), dtype=self.dtype)

    def relu(self) -> "Tensor":
        return Tensor(self._tensor.relu(), dtype=self.dtype)

    def sigmoid(self) -> "Tensor":
        return Tensor(self._tensor.sigmoid(), dtype=self.dtype)

    def detach(self) -> "Tensor":
        return Tensor(self.tolist(), dtype=self.dtype)

    def numpy(self) -> Any:
        try:
            import numpy as np  # type: ignore
            return np.array(self.tolist())
        except Exception:
            return self.tolist()

    def __add__(self, other: Any) -> "Tensor":
        return Tensor(self._tensor + _unwrap(other), dtype=self.dtype)

    def __radd__(self, other: Any) -> "Tensor":
        return self.__add__(other)

    def __sub__(self, other: Any) -> "Tensor":
        return Tensor(self._tensor - _unwrap(other), dtype=self.dtype)

    def __rsub__(self, other: Any) -> "Tensor":
        # Ensure scalar - tensor broadcasts through the tensor-shaped left side.
        return Tensor((self._tensor * -1.0) + _unwrap(other), dtype=self.dtype)

    def __mul__(self, other: Any) -> "Tensor":
        return Tensor(self._tensor * _unwrap(other), dtype=self.dtype)

    def __rmul__(self, other: Any) -> "Tensor":
        return self.__mul__(other)

    def __truediv__(self, other: Any) -> "Tensor":
        other_unwrapped = _unwrap(other)
        if isinstance(other_unwrapped, NDTensor):
            if other_unwrapped.shape != ():
                raise TorchCompatError("elementwise tensor division is not implemented yet")
            other_unwrapped = other_unwrapped.data[0]
        return Tensor(self._tensor * (1.0 / float(other_unwrapped)), dtype=self.dtype)

    def __pow__(self, power: float) -> "Tensor":
        return Tensor(self._tensor ** power, dtype=self.dtype)

    def __matmul__(self, other: Any) -> "Tensor":
        return matmul(self, other)

    def __repr__(self) -> str:
        return f"agilang.tensor({self.tolist()}, shape={self.shape}, requires_grad={self.requires_grad})"


def tensor(data: Any, *, dtype: str = float32, device: str = "cpu", requires_grad: bool = False) -> Tensor:
    return Tensor(data, dtype=dtype, device=device, requires_grad=requires_grad)


def as_tensor(data: Any, *, dtype: str = float32, device: str = "cpu") -> Tensor:
    return tensor(data, dtype=dtype, device=device)


def zeros(shape: Sequence[int], *, dtype: str = float32, device: str = "cpu", requires_grad: bool = False) -> Tensor:
    def build(dims: list[int]) -> Any:
        if not dims:
            return 0.0
        return [build(dims[1:]) for _ in range(int(dims[0]))]
    return tensor(build(list(shape)), dtype=dtype, device=device, requires_grad=requires_grad)


def ones(shape: Sequence[int], *, dtype: str = float32, device: str = "cpu", requires_grad: bool = False) -> Tensor:
    def build(dims: list[int]) -> Any:
        if not dims:
            return 1.0
        return [build(dims[1:]) for _ in range(int(dims[0]))]
    return tensor(build(list(shape)), dtype=dtype, device=device, requires_grad=requires_grad)


def arange(start: int, end: int | None = None, step: int = 1, *, dtype: str = float32, device: str = "cpu") -> Tensor:
    if step == 0:
        raise ValueError("step must not be zero")
    if end is None:
        start, end = 0, start
    return tensor([float(v) for v in range(int(start), int(end), int(step))], dtype=dtype, device=device)


def matmul(a: Any, b: Any) -> Tensor:
    ta = a._tensor if isinstance(a, Tensor) else ndtensor(a)
    tb = b._tensor if isinstance(b, Tensor) else ndtensor(b)
    return Tensor(_nd_matmul(ta, tb))


def mm(a: Any, b: Any) -> Tensor:
    return matmul(a, b)


def relu(x: Any) -> Tensor:
    return Tensor((x._tensor if isinstance(x, Tensor) else ndtensor(x)).relu())


def sigmoid(x: Any) -> Tensor:
    return Tensor((x._tensor if isinstance(x, Tensor) else ndtensor(x)).sigmoid())


def softmax(x: Any, dim: int = -1) -> Tensor:
    t = x if isinstance(x, Tensor) else tensor(x)
    values = t.tolist()
    if len(t.shape) == 2 and dim in {-1, 1}:
        return tensor([_softmax_vector(row) for row in values])
    return tensor(_nd_softmax(t._tensor))


def _softmax_vector(values: Sequence[float]) -> list[float]:
    vals = [float(v) for v in values]
    top = max(vals) if vals else 0.0
    exp = [math.exp(v - top) for v in vals]
    total = sum(exp) or 1.0
    return [v / total for v in exp]


def mse_loss(prediction: Any, target: Any) -> Tensor:
    pred = prediction._tensor if isinstance(prediction, Tensor) else ndtensor(prediction)
    truth = target._tensor if isinstance(target, Tensor) else ndtensor(target)
    return Tensor(_nd_mse(pred, truth))


class Module:
    def parameters(self) -> list[Tensor]:
        params: list[Tensor] = []
        for value in self.__dict__.values():
            if isinstance(value, Parameter):
                params.append(value)
            elif isinstance(value, Module):
                params.extend(value.parameters())
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, Module):
                        params.extend(item.parameters())
                    elif isinstance(item, Parameter):
                        params.append(item)
        return params

    def zero_grad(self) -> None:
        for parameter in self.parameters():
            parameter.zero_grad()

    def state_dict(self) -> dict[str, Any]:
        state: dict[str, Any] = {}
        for name, value in self.__dict__.items():
            if isinstance(value, Parameter):
                state[name] = value.tolist()
            elif isinstance(value, Module):
                for k, v in value.state_dict().items():
                    state[f"{name}.{k}"] = v
            elif isinstance(value, list):
                for idx, item in enumerate(value):
                    if isinstance(item, Module):
                        for k, v in item.state_dict().items():
                            state[f"{name}.{idx}.{k}"] = v
        return state

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.forward(*args, **kwargs)

    def forward(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


class Parameter(Tensor):
    def __init__(self, data: Any, *, dtype: str = float32) -> None:
        if isinstance(data, Tensor):
            super().__init__(data.tolist(), requires_grad=True, dtype=dtype)
        else:
            super().__init__(data, requires_grad=True, dtype=dtype)


class Linear(Module):
    def __init__(self, in_features: int, out_features: int, *, bias: bool = True) -> None:
        import random
        scale = 1.0 / math.sqrt(max(1, in_features))
        rnd = random.Random(in_features * 1009 + out_features)
        self.weight = Parameter([[rnd.uniform(-scale, scale) for _ in range(out_features)] for _ in range(in_features)])
        self.bias = Parameter([0.0 for _ in range(out_features)]) if bias else None

    def forward(self, x: Any) -> Tensor:
        out = matmul(x, self.weight)
        if self.bias is not None:
            from .ndtensor_broadcast import broadcast_add
            return Tensor(broadcast_add(out._tensor, self.bias._tensor))
        return out


class ReLU(Module):
    def forward(self, x: Any) -> Tensor:
        return relu(x)


class Sigmoid(Module):
    def forward(self, x: Any) -> Tensor:
        return sigmoid(x)


class Sequential(Module):
    def __init__(self, *layers: Module) -> None:
        self.layers = list(layers)

    def forward(self, x: Any) -> Any:
        out = x
        for layer in self.layers:
            out = layer(out)
        return out

    def parameters(self) -> list[Tensor]:
        params: list[Tensor] = []
        for layer in self.layers:
            params.extend(layer.parameters())
        return params

    def state_dict(self) -> dict[str, Any]:
        state: dict[str, Any] = {}
        for idx, layer in enumerate(self.layers):
            for key, value in layer.state_dict().items():
                state[f"{idx}.{key}"] = value
        return state


class SGD:
    def __init__(self, params: Iterable[Tensor], lr: float = 0.01) -> None:
        self.params = list(params)
        self.lr = float(lr)

    def zero_grad(self) -> None:
        for parameter in self.params:
            parameter.zero_grad()

    def step(self) -> None:
        sgd_step([parameter._tensor for parameter in self.params], learning_rate=self.lr)


@dataclass
class _NNNamespace:
    Module: type = Module
    Parameter: type = Parameter
    Linear: type = Linear
    ReLU: type = ReLU
    Sigmoid: type = Sigmoid
    Sequential: type = Sequential


@dataclass
class _OptimNamespace:
    SGD: type = SGD


nn = _NNNamespace()
optim = _OptimNamespace()


def save(obj: Any, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, Module):
        payload = {"format": TORCH_COMPAT_FORMAT, "type": "state_dict", "state": obj.state_dict()}
    elif isinstance(obj, Tensor):
        payload = {"format": TORCH_COMPAT_FORMAT, "type": "tensor", "data": obj.tolist(), "requires_grad": obj.requires_grad}
    else:
        payload = {"format": TORCH_COMPAT_FORMAT, "type": "object", "data": obj}
    p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return str(p)


def load(path: str | Path) -> Any:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("format") != TORCH_COMPAT_FORMAT:
        raise ValueError(f"unsupported torch compatibility artifact: {payload.get('format')}")
    if payload.get("type") == "tensor":
        return tensor(payload["data"], requires_grad=bool(payload.get("requires_grad", False)))
    return payload.get("state", payload.get("data"))


def torch_compat_status() -> dict[str, Any]:
    return {
        "format": TORCH_COMPAT_FORMAT,
        "backend": "agilang-native-ndtensor",
        "implemented": [
            "Tensor wrapper",
            "tensor/as_tensor/zeros/ones/arange",
            "recursive list tensor shapes through NDTensor",
            "autograd for scalar loss graphs supported by NDTensor",
            "matmul/mm/relu/sigmoid/softmax/mse_loss",
            "nn.Module/Parameter/Linear/ReLU/Sigmoid/Sequential",
            "optim.SGD",
            "save/load JSON artifacts",
        ],
        "not_full_pytorch_yet": [
            "full operator catalogue",
            "TorchScript/FX/Dynamo parity",
            "CUDA dispatcher parity",
            "distributed torch parity",
            "full serialization/checkpoint compatibility",
        ],
        "production_boundary": "PyTorch-compatible native subset for AGILANG apps, not a drop-in full torch package replacement.",
    }


__all__ = [
    "TORCH_COMPAT_FORMAT",
    "TorchCompatError",
    "Tensor",
    "tensor",
    "as_tensor",
    "zeros",
    "ones",
    "arange",
    "matmul",
    "mm",
    "relu",
    "sigmoid",
    "softmax",
    "mse_loss",
    "Module",
    "Parameter",
    "Linear",
    "ReLU",
    "Sigmoid",
    "Sequential",
    "SGD",
    "nn",
    "optim",
    "save",
    "load",
    "torch_compat_status",
    "float32",
    "float64",
    "int64",
    "long",
]
