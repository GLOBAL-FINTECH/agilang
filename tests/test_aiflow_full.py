from __future__ import annotations

from pathlib import Path

from agilang.aiflow_full import (
    Adam,
    Conv2D,
    Dataset,
    GradientTape,
    LSTM,
    MultiHeadAttention,
    Variable,
    compatibility_bridge,
    gpu_backends,
    load_architecture,
    replacement_matrix,
    save_architecture,
)


def test_gradient_tape_and_adam_update_variable() -> None:
    weight = Variable(0.0, name="weight")
    tape = GradientTape()

    def loss() -> float:
        return (weight.value - 3.0) ** 2

    grads = tape.gradient(loss, [weight])
    assert round(grads[0], 3) == -6.0
    opt = Adam(learning_rate=0.1)
    before = weight.value
    opt.apply_gradients([(grads[0], weight)])
    assert weight.value > before


def test_dataset_batch_shuffle_map() -> None:
    ds = Dataset.from_tensor_slices([1, 2, 3, 4]).map(lambda x: x * 2).shuffle(seed=1)
    batches = ds.batch(2)
    assert len(batches) == 2
    assert sorted(v for batch in batches for v in batch) == [2, 4, 6, 8]


def test_full_replacement_architecture_specs_and_bridges(tmp_path: Path) -> None:
    layers = [Conv2D(8, 3, activation="relu"), LSTM(4), MultiHeadAttention(2, 8)]
    path = tmp_path / "models" / "vision-language.agi-arch.json"
    save_architecture(path, layers, {"name": "vision-language"})
    loaded = load_architecture(path)
    assert loaded["format"] == "agilang-aiflow-architecture"
    assert loaded["layers"][0]["filters"] == 8
    assert "cuda" in gpu_backends()
    assert "tensorflow" in compatibility_bridge()
    matrix = replacement_matrix()
    assert "Conv2D" in matrix["architecture_ready"]
    assert "full TensorFlow SavedModel compatibility" in matrix["not_claimed_complete_yet"]
