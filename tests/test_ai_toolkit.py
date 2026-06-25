from __future__ import annotations

from pathlib import Path

from agilang.ai import (
    ai_runtime_info,
    ai_select_backend,
    audio_pipeline,
    chart_spec,
    dataset_summary,
    kmeans,
    linear_regression,
    logistic_regression,
    minmax_scale,
    model_load,
    model_save,
    neural_network_predict,
    neural_network_train,
    predict_linear,
    predict_logistic,
    tensor,
    tensor_matmul,
    tensor_shape,
    video_pipeline,
)


def test_tensor_scientific_computing_and_runtime_selection() -> None:
    a = tensor([[1, 2], [3, 4]], device="cpu")
    b = tensor([[5], [6]], device="cpu")
    out = tensor_matmul(a, b)
    assert tensor_shape(out) == [2, 1]
    assert out.tolist() == [[17.0], [39.0]]
    backend = ai_select_backend()
    assert backend["ok"] is True
    assert ai_runtime_info()["backends"]["native"] is True


def test_data_processing_and_ml_models(tmp_path: Path) -> None:
    rows = [{"x": 1, "y": 2, "class": 0}, {"x": 2, "y": 4, "class": 0}, {"x": 3, "y": 6, "class": 1}, {"x": 4, "y": 8, "class": 1}]
    summary = dataset_summary(rows)
    assert summary["rows"] == 4
    assert summary["numeric"]["x"]["mean"] == 2.5
    scaled = minmax_scale(rows, ["x", "y"])
    assert scaled[0]["x"] == 0.0
    assert scaled[-1]["y"] == 1.0

    linear = linear_regression(rows, ["x"], "y")
    assert round(linear["weights"]["x"], 6) == 2.0
    assert predict_linear(linear, {"x": 10}) == 20.0

    logistic = logistic_regression(rows, ["x"], "class", epochs=100)
    assert predict_logistic(logistic, {"x": 4}) in {0, 1}

    clusters = kmeans([[0, 0], [0, 1], [9, 9], [9, 8]], k=2)
    assert len(clusters["centers"]) == 2

    path = tmp_path / "models" / "linear.agi-model"
    model_save(path, linear)
    assert model_load(path)["type"] == "linear_regression"


def test_deep_learning_starter_and_multimedia_pipeline_specs() -> None:
    model = neural_network_train([[0], [1], [2], [3]], [[0], [2], [4], [6]], hidden=3, epochs=20)
    pred = neural_network_predict(model, [4])
    assert len(pred) == 1
    assert isinstance(pred[0], float)
    assert chart_spec("line", [{"x": 1, "y": 2}])["renderer"] == "ags"
    assert "speech_to_text" in audio_pipeline()["supported"]
    assert "object_detection" in video_pipeline("object_detection")["supported"]
