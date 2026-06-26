from __future__ import annotations

from agilang.cnn_training_loop_v1 import (
    AdamMultiFilterState,
    adam_update_multifilter,
    relu_feature_maps,
    relu_feature_maps_backward,
    train_cnn_feature_step,
)


def _image():
    return [
        [[1, 1], [1, 1]],
        [[1, 1], [1, 1]],
    ]


def _kernels():
    return [
        [
            [[0.0, 0.0], [0.0, 0.0]],
            [[0.0, 0.0], [0.0, 0.0]],
        ]
    ]


def test_relu_feature_maps_forward_and_backward() -> None:
    relu = relu_feature_maps([[[-1.0, 2.0], [3.0, -4.0]]])
    assert relu["output"] == [[[0.0, 2.0], [3.0, 0.0]]]
    assert relu["mask"] == [[[0.0, 1.0], [1.0, 0.0]]]
    grad = relu_feature_maps_backward([[[5.0, 5.0], [5.0, 5.0]]], relu["mask"])
    assert grad == [[[0.0, 5.0], [5.0, 0.0]]]


def test_adam_update_multifilter_updates_weights() -> None:
    kernels = _kernels()
    grads = [[[[[-1.0, -1.0], [-1.0, -1.0]], [[-1.0, -1.0], [-1.0, -1.0]]]][0]]
    state = AdamMultiFilterState()
    result = adam_update_multifilter(kernels, grads, [0.0], [-1.0], state=state, learning_rate=0.01)
    assert result["state"].t == 1
    assert result["kernels"][0][0][0][0] > 0.0
    assert result["biases"][0] > 0.0


def test_train_cnn_feature_step_moves_zero_filter_toward_positive_target() -> None:
    image = _image()
    kernels = _kernels()
    target = [[[2.0]]]
    step = train_cnn_feature_step(image, kernels, target, learning_rate=0.01)
    assert step["loss"] == 4.0
    assert step["kernels"][0][0][0][0] > 0.0
    second = train_cnn_feature_step(image, step["kernels"], target, biases=step["biases"], optimizer_state=step["optimizer_state"], learning_rate=0.01)
    assert second["optimizer_state"].t == 2
    assert second["loss"] <= step["loss"]
