from __future__ import annotations

from pathlib import Path

from agilang.aiflow import Dense, SGD, Sequential, keras, load_model, matmul, ones, zeros


def test_aiflow_tensor_helpers() -> None:
    assert zeros([2, 2]).tolist() == [[0.0, 0.0], [0.0, 0.0]]
    assert ones([2]).tolist() == [1.0, 1.0]
    assert matmul([[1, 2], [3, 4]], [[5], [6]]).tolist() == [[17.0], [39.0]]


def test_sequential_regression_training_and_model_save_load(tmp_path: Path) -> None:
    model = Sequential([
        Dense(4, activation="relu", input_shape=[1]),
        Dense(1, activation="linear"),
    ])
    model.compile(optimizer=SGD(0.01), loss="mse")
    history = model.fit([[0], [1], [2], [3]], [[0], [2], [4], [6]], epochs=80)
    assert history["loss"][-1] < history["loss"][0]
    pred = model.predict([[4]])[0][0]
    assert isinstance(pred, float)
    path = tmp_path / "model.agi-model"
    model.save(path)
    loaded = load_model(path)
    assert loaded.predict([[4]])[0][0] == model.predict([[4]])[0][0]


def test_keras_style_aliases_for_tensorflow_replacement_api() -> None:
    model = keras.Sequential([
        keras.layers.Dense(2, activation="relu", input_shape=[1]),
        keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer=keras.optimizers.SGD(0.05), loss=keras.losses.binary_crossentropy, metrics=[keras.metrics.binary_accuracy])
    history = model.fit([[0], [1], [2], [3]], [[0], [0], [1], [1]], epochs=20)
    assert "binary_accuracy" in history
    result = model.evaluate([[0], [3]], [[0], [1]])
    assert "loss" in result
    assert "binary_accuracy" in result
