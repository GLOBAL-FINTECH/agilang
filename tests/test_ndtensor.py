from __future__ import annotations

from agilang.ndtensor import matmul, mse, ndtensor, sgd_step, softmax, variable


def test_ndtensor_shape_ops_and_matmul() -> None:
    a = ndtensor([[1, 2], [3, 4]])
    b = ndtensor([[5], [6]])
    out = matmul(a, b)
    assert out.shape == (2, 1)
    assert out.tolist() == [[17.0], [39.0]]
    assert softmax([1, 2, 3])[-1] > softmax([1, 2, 3])[0]


def test_reverse_mode_autodiff_scalar_loss() -> None:
    w = variable(0.0, name="w")
    x = ndtensor(3.0)
    y = ndtensor(6.0)
    pred = w * x
    loss = mse(pred, y)
    loss.backward()
    assert round(w.grad[0], 3) == -36.0


def test_sgd_step_learns_simple_weight() -> None:
    w = variable(0.0, name="w")
    for _ in range(25):
        pred = w * ndtensor(2.0)
        loss = mse(pred, ndtensor(4.0))
        loss.backward()
        sgd_step([w], learning_rate=0.05)
    assert abs(w.item() - 2.0) < 0.05


def test_matmul_backward_gradients() -> None:
    a = variable([[1.0, 2.0]], name="a")
    b = variable([[3.0], [4.0]], name="b")
    out = matmul(a, b).sum()
    out.backward()
    assert a.grad == [3.0, 4.0]
    assert b.grad == [1.0, 2.0]
