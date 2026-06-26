from pathlib import Path

from agilang.ml import (
    ai_runtime_info,
    ml_chart_spec,
    ml_confusion_matrix,
    ml_decision_stump,
    ml_kmeans,
    ml_linear_regression,
    ml_load_model,
    ml_logistic_regression,
    ml_neural_network_predict,
    ml_neural_network_train,
    ml_predict_linear,
    ml_predict_logistic,
    ml_predict_tree,
    ml_save_model,
    tensor_matmul,
    tensor_shape,
    tensor_softmax,
)


def test_tensor_and_scientific_helpers_work():
    assert tensor_shape([[1, 2], [3, 4]]) == [2, 2]
    assert tensor_matmul([[1, 2]], [[3], [4]]) == [[11.0]]
    probs = tensor_softmax([1, 2, 3])
    assert round(sum(probs), 6) == 1.0
    assert probs[-1] > probs[0]


def test_classical_ml_algorithms_and_persistence(tmp_path: Path):
    rows = [
        {"x": 1, "y": 2, "label": 0},
        {"x": 2, "y": 4, "label": 0},
        {"x": 3, "y": 6, "label": 1},
        {"x": 4, "y": 8, "label": 1},
    ]
    linear = ml_linear_regression(rows, "y", ["x"])
    assert round(ml_predict_linear(linear, {"x": 10}), 6) == 20.0

    logistic = ml_logistic_regression(rows, "label", ["x"], epochs=300)
    assert ml_predict_logistic(logistic, {"x": 4})["class"] == 1

    clusters = ml_kmeans(rows, ["x", "y"], k=2)
    assert len(clusters["assignments"]) == 4

    stump = ml_decision_stump(rows, "label", ["x"])
    assert ml_predict_tree(stump, {"x": 4}) == 1

    cm = ml_confusion_matrix([0, 1, 1], [0, 1, 0])
    assert cm["matrix"]["1"]["1"] == 1

    path = tmp_path / "model.agi-model"
    assert ml_save_model(linear, path)["ok"] is True
    assert ml_load_model(path)["type"] == "linear_regression"


def test_neural_network_runtime_and_visualization():
    rows = [
        {"a": 0, "b": 0, "label": 0},
        {"a": 0, "b": 1, "label": 1},
        {"a": 1, "b": 0, "label": 1},
        {"a": 1, "b": 1, "label": 1},
    ]
    model = ml_neural_network_train(rows, "label", ["a", "b"], hidden=3, epochs=150)
    assert model["type"] == "neural_network_binary"
    pred = ml_neural_network_predict(model, {"a": 1, "b": 0})
    assert 0 <= pred["probability"] <= 1
    chart = ml_chart_spec(rows, "scatter", "a", "b", "Logic data")
    assert chart["chart"] == "scatter"
    info = ai_runtime_info()
    assert "ram" in info and "gpu" in info
