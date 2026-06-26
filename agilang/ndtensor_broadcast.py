"""Broadcasting helpers for AGILANG NDTensor.

Adds safe row-bias broadcasting and gradient reduction helpers for dense layers
without replacing the base NDTensor engine.
"""
from __future__ import annotations

from .ndtensor import NDTensor, ndtensor


def broadcast_add(left: NDTensor, right: NDTensor) -> NDTensor:
    left = ndtensor(left)
    right = ndtensor(right)

    if left.shape == right.shape:
        out_shape = left.shape
        ldata, rdata = left.data, right.data
        reduce_left = lambda g: list(g)
        reduce_right = lambda g: list(g)
    elif right.shape == ():
        out_shape = left.shape
        ldata = left.data
        rdata = [right.data[0] for _ in left.data]
        reduce_left = lambda g: list(g)
        reduce_right = lambda g: [sum(g)]
    elif len(left.shape) == 2 and right.shape in {(left.shape[1],), (1, left.shape[1])}:
        rows, cols = left.shape
        out_shape = left.shape
        ldata = left.data
        rdata = [right.data[j] for _ in range(rows) for j in range(cols)]
        reduce_left = lambda g: list(g)
        reduce_right = lambda g: [sum(g[i * cols + j] for i in range(rows)) for j in range(cols)]
    else:
        raise ValueError(f"unsupported broadcast_add shapes: {left.shape} and {right.shape}")

    out = NDTensor([a + b for a, b in zip(ldata, rdata)], out_shape, left.requires_grad or right.requires_grad, parents=[left, right])

    def back(g: list[float]) -> None:
        left._accumulate_grad(reduce_left(g))
        right._accumulate_grad(reduce_right(g))

    out.backward_fn = back
    return out


def activate(x: NDTensor, name: str | None) -> NDTensor:
    if name in (None, "linear"):
        return x
    if name == "relu":
        return x.relu()
    if name == "sigmoid":
        return x.sigmoid()
    if name == "tanh":
        vals = [__import__('math').tanh(v) for v in x.data]
        out = NDTensor(vals, x.shape, x.requires_grad, parents=[x])
        def back(g: list[float]) -> None:
            x._accumulate_grad([gv * (1.0 - y * y) for gv, y in zip(g, vals)])
        out.backward_fn = back
        return out
    raise ValueError(f"unsupported activation: {name}")


__all__ = ["broadcast_add", "activate"]
