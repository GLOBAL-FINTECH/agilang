from __future__ import annotations

from pathlib import Path

from agilang.aiflow_native_v2 import NativeDenseV2, NativeSequentialV2, load_native_v2_model, native_mlp
from agilang.ndtensor import ndtensor, variable
from agilang.ndtensor_broadcast import broadcast_add


def test_broadcast_add_bias_gradient() -> None:
    x = ndtensor([[1.0, 2.0], [3.0, 4.0]])
    b = variable([10.0, 20.0], name="bias")
    out = broadcast_add(x, b).sum()
    out.backward()
    assert b.grad == [2.0, 2.0]


def test_native_mlp_trains_with_relu() -> None:
    model = native_mlp(input_dim=1, hidden=4, output_dim=1, activation="relu")
    history = model.fit([[0], [1], [2], [3]], [[0], [2], [4], [6]], epochs=80, learning_rate=0.02)
    assert history["loss"][-1] < history["loss"][0]
    assert len(model.predict([[4]])) == 1


def test_native_v2_save_load(tmp_path: Path) -> None:
    model = NativeSequentialV2([NativeDenseV2(2, 1, activation="relu"), NativeDenseV2(1, 2)])
    model.fit([[1], [2]], [[2], [4]], epochs=5, learning_rate=0.01)
    path = tmp_path / "native-v2.agi-model"
    model.save(path)
    loaded = load_native_v2_model(path)
    assert loaded.predict([[3]]) == model.predict([[3]])
