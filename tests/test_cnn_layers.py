from __future__ import annotations

from pathlib import Path

from agilang.cnn_layers import CNNClassifier, cnn_multi_filter_features, conv2d_multi_filter, load_cnn_classifier


def _image():
    return [
        [[255, 0, 0], [0, 255, 0]],
        [[0, 0, 255], [255, 255, 255]],
    ]


def _kernels():
    return [
        [
            [[1, 0, 0], [0, 1, 0]],
            [[0, 0, 1], [1, 1, 1]],
        ],
        [
            [[0, 1, 0], [1, 0, 0]],
            [[1, 1, 1], [0, 0, 1]],
        ],
    ]


def test_conv2d_multi_filter_returns_feature_map_per_filter() -> None:
    maps = conv2d_multi_filter(_image(), _kernels())
    assert len(maps) == 2
    assert maps[0] == [[6.0]]
    assert maps[1] == [[6.0]]


def test_cnn_multi_filter_features_flatten_all_filters() -> None:
    result = cnn_multi_filter_features(_image(), _kernels(), pool_size=1)
    assert result["features"] == [6.0, 6.0]
    assert len(result["feature_maps"]) == 2


def test_cnn_classifier_predict_and_save_load(tmp_path: Path) -> None:
    model = CNNClassifier(
        kernels=_kernels(),
        dense_weights=[[0.1, 2.0], [0.1, 2.0]],
        labels=["low", "high"],
        pool_size=1,
    )
    result = model.predict(_image())
    assert result["predicted_label"] == "high"
    path = tmp_path / "models" / "cnn.agi-model"
    model.save(path)
    loaded = load_cnn_classifier(path)
    assert loaded.predict(_image())["predicted_label"] == "high"
