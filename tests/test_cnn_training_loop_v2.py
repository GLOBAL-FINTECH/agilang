from __future__ import annotations

from pathlib import Path

from agilang.cnn_training_loop_v2 import (
    NativeCNNClassifierV2,
    dense_backward,
    dense_forward,
    flatten_feature_maps,
    load_native_cnn_v2,
    softmax_cross_entropy,
    unflatten_feature_maps,
)


def _image():
    return [
        [[1, 1], [1, 1]],
        [[1, 1], [1, 1]],
    ]


def _kernels():
    return [
        [
            [[1.0, 0.0], [0.0, 1.0]],
            [[1.0, 1.0], [0.0, 0.0]],
        ]
    ]


def test_flatten_unflatten_feature_maps_roundtrip() -> None:
    maps = [[[1.0, 2.0], [3.0, 4.0]], [[5.0]]]
    flat = flatten_feature_maps(maps)
    assert flat["values"] == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert unflatten_feature_maps(flat["values"], flat["shapes"]) == maps


def test_dense_forward_loss_and_backward() -> None:
    features = [1.0, 2.0]
    weights = [[1.0, 0.0], [0.0, 1.0]]
    bias = [0.0, 0.0]
    scores = dense_forward(features, weights, bias)
    assert scores == [1.0, 2.0]
    loss = softmax_cross_entropy(scores, 1)
    assert loss["loss"] > 0
    grads = dense_backward(features, weights, loss["grad_scores"])
    assert len(grads["grad_weights"]) == 2
    assert len(grads["grad_features"]) == 2


def test_native_cnn_v2_predict_train_and_save_load(tmp_path: Path) -> None:
    model = NativeCNNClassifierV2.create(_kernels(), labels=["low", "high"], feature_count=1, seed=1, pool_size=1)
    before = model.train_step(_image(), label_index=1, learning_rate=0.01)
    after = model.train_step(_image(), label_index=1, learning_rate=0.01)
    assert after["loss"] <= before["loss"] or after["predicted"]["predicted_label"] == "high"
    pred = model.predict(_image())
    assert pred["predicted_label"] in {"low", "high"}
    history = model.fit([_image()], [1], epochs=2, learning_rate=0.01)
    assert len(history["loss"]) == 2
    path = tmp_path / "models" / "cnn-v2.agi-model"
    model.save(path)
    loaded = load_native_cnn_v2(path)
    assert loaded.predict(_image())["predicted_label"] in {"low", "high"}
