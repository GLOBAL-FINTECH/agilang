from __future__ import annotations

from agilang.conv2d_multichannel_training import (
    conv2d_multi_channel_backward,
    conv2d_multi_channel_forward,
    conv2d_multi_filter_backward,
    conv2d_multi_filter_forward,
    mse_feature_maps,
)


def test_multi_channel_conv_forward_and_backward() -> None:
    image = [
        [[1, 2], [3, 4]],
        [[5, 6], [7, 8]],
    ]
    kernel = [
        [[1, 0], [0, 1]],
        [[1, 1], [0, 0]],
    ]
    out = conv2d_multi_channel_forward(image, kernel)
    assert out == [[12.0]]
    grads = conv2d_multi_channel_backward(image, kernel, [[1.0]])
    assert grads["grad_kernel"] == image
    assert grads["grad_bias"] == 1.0
    assert grads["grad_image"][0][0] == [1.0, 0.0]
    assert grads["grad_image"][1][0] == [1.0, 1.0]


def test_multi_filter_conv_backward_accumulates_image_gradients() -> None:
    image = [
        [[1, 1], [1, 1]],
        [[1, 1], [1, 1]],
    ]
    kernels = [
        [[[1, 0], [0, 1]], [[0, 0], [1, 1]]],
        [[[0, 1], [1, 0]], [[1, 1], [0, 0]]],
    ]
    outs = conv2d_multi_filter_forward(image, kernels)
    assert outs == [[[4.0]], [[4.0]]]
    loss, grad_outputs = mse_feature_maps(outs, [[[5.0]], [[3.0]]])
    assert loss == 1.0
    grads = conv2d_multi_filter_backward(image, kernels, grad_outputs)
    assert len(grads["grad_kernels"]) == 2
    assert len(grads["grad_biases"]) == 2
    assert grads["grad_biases"] == [-1.0, 1.0]
    assert grads["grad_image"][0][0] == [-1.0, 1.0]
