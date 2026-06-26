from __future__ import annotations

from agilang.vision_kernels import (
    avgpool2d,
    cnn_feature_pipeline,
    conv2d_single_channel,
    flatten,
    image_shape,
    image_to_patches,
    maxpool2d,
    normalize_image,
    relu_image,
)


def test_conv2d_single_channel_forward() -> None:
    image = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    kernel = [
        [1, 0],
        [0, 1],
    ]
    assert conv2d_single_channel(image, kernel) == [[6.0, 8.0], [12.0, 14.0]]


def test_pooling_flatten_and_patches() -> None:
    image = [
        [1, 2, 3, 4],
        [5, 6, 7, 8],
        [9, 10, 11, 12],
        [13, 14, 15, 16],
    ]
    assert maxpool2d(image, 2) == [[6.0, 8.0], [14.0, 16.0]]
    assert avgpool2d(image, 2) == [[3.5, 5.5], [11.5, 13.5]]
    assert flatten([[1, 2], [3, 4]]) == [1.0, 2.0, 3.0, 4.0]
    assert len(image_to_patches(image, 2, 2)) == 4


def test_cnn_feature_pipeline() -> None:
    image = [
        [0, 0, 0],
        [0, 255, 0],
        [0, 0, 0],
    ]
    kernel = [[1, 1], [1, 1]]
    result = cnn_feature_pipeline(image, kernel, pool_size=2)
    assert result["input_shape"] == [3, 3]
    assert result["conv_shape"] == [2, 2]
    assert result["pool_shape"] == [1, 1]
    assert result["features"] == [1.0]
    assert normalize_image([[0, 255]]) == [[0.0, 1.0]]
    assert relu_image([[-1, 2]]) == [[0.0, 2.0]]
    assert image_shape([[[1], [2]]]) == [1, 2, 1]
