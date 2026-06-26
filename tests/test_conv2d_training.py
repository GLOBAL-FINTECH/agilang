from __future__ import annotations

from agilang.conv2d_training import conv2d_backward, conv2d_forward, mse_loss, train_conv2d_step


def test_conv2d_forward_and_mse_gradient() -> None:
    image = [[1, 2], [3, 4]]
    kernel = [[1, 0], [0, 1]]
    pred = conv2d_forward(image, kernel)
    assert pred == [[5.0]]
    loss, grad = mse_loss(pred, [[7]])
    assert loss == 4.0
    assert grad == [[-4.0]]


def test_conv2d_backward_kernel_image_bias_gradients() -> None:
    image = [[1, 2], [3, 4]]
    kernel = [[1, 0], [0, 1]]
    grads = conv2d_backward(image, kernel, [[1.0]])
    assert grads["grad_kernel"] == [[1.0, 2.0], [3.0, 4.0]]
    assert grads["grad_image"] == [[1.0, 0.0], [0.0, 1.0]]
    assert grads["grad_bias"] == 1.0


def test_train_conv2d_step_reduces_loss_direction() -> None:
    image = [[1, 2], [3, 4]]
    kernel = [[0, 0], [0, 0]]
    before = conv2d_forward(image, kernel)[0][0]
    step = train_conv2d_step(image, kernel, [[10]], learning_rate=0.01)
    after = conv2d_forward(image, step["kernel"], bias=step["bias"])[0][0]
    assert before == 0.0
    assert after > before
    assert step["loss"] == 100.0
