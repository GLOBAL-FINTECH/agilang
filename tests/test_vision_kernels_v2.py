from __future__ import annotations

from agilang.vision_kernels_v2 import (
    argmax,
    benchmark_conv2d,
    conv2d_multi_channel,
    image_classifier_pipeline,
    normalize_rgb,
    softmax,
)


def test_softmax_argmax_helpers() -> None:
    probs = softmax([1, 2, 3])
    assert round(sum(probs), 6) == 1.0
    assert argmax(probs) == 2


def test_conv2d_multi_channel_rgb_forward() -> None:
    image = [
        [[255, 0, 0], [0, 255, 0]],
        [[0, 0, 255], [255, 255, 255]],
    ]
    kernel = [
        [[1, 0, 0], [0, 1, 0]],
        [[0, 0, 1], [1, 1, 1]],
    ]
    out = conv2d_multi_channel(image, kernel)
    assert out == [[6.0]]
    assert normalize_rgb([[[0, 255, 127.5]]]) == [[[0.0, 1.0, 0.5]]]


def test_image_classifier_pipeline_predicts_label() -> None:
    image = [
        [[255, 0, 0], [0, 255, 0]],
        [[0, 0, 255], [255, 255, 255]],
    ]
    kernel = [
        [[1, 0, 0], [0, 1, 0]],
        [[0, 0, 1], [1, 1, 1]],
    ]
    weights = [[0.1, 2.0]]
    result = image_classifier_pipeline(image, kernel, weights, ["low", "high"], pool_size=1)
    assert result["predicted_label"] == "high"
    assert result["probabilities"][1] > result["probabilities"][0]


def test_benchmark_conv2d_reports_shape() -> None:
    image = [
        [[1, 1, 1], [1, 1, 1]],
        [[1, 1, 1], [1, 1, 1]],
    ]
    kernel = [
        [[1, 1, 1]],
    ]
    result = benchmark_conv2d(image, kernel, repeats=1)
    assert result["engine"] == "agilang-native-reference"
    assert result["output_shape"] == [2, 2]
