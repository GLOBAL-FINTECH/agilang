from __future__ import annotations

from pathlib import Path

from agilang.aiflow_native import NativeDense, NativeSequential, load_native_model, native_linear_model


def test_native_aiflow_linear_model_learns_simple_relation() -> None:
    model = native_linear_model(input_dim=1, output_dim=1)
    history = model.fit([[0], [1], [2], [3]], [[0], [2], [4], [6]], epochs=60, learning_rate=0.05)
    assert history["loss"][-1] < history["loss"][0]
    pred = model.predict([[4]])[0][0]
    assert abs(pred - 8.0) < 1.0


def test_native_aiflow_save_load_roundtrip(tmp_path: Path) -> None:
    model = NativeSequential([NativeDense(1, 1)])
    model.fit([[1], [2]], [[2], [4]], epochs=10, learning_rate=0.02)
    path = tmp_path / "models" / "native.agi-model"
    model.save(path)
    loaded = load_native_model(path)
    assert loaded.predict([[3]])[0][0] == model.predict([[3]])[0][0]
