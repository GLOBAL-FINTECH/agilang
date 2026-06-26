from __future__ import annotations

from pathlib import Path

from agilang.agirecord import AGIRecordDataset, read_agirecord, write_agirecord
from agilang.ai_benchmarks import time_call
from agilang.cnn_batch_trainer import evaluate_cnn, train_cnn_batches
from agilang.cnn_training_loop_v2 import NativeCNNClassifierV2
from agilang.model_exchange import export_descriptor, onnx_bridge_status
from agilang.tokenizer_engine import VocabTokenizer
from agilang.transformer_blocks import transformer_stack


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


def test_agirecord_save_load_shuffle_batch(tmp_path: Path) -> None:
    path = tmp_path / "data" / "demo.agi-record"
    write_agirecord(path, [_image(), _image()], [0, 1])
    dataset = read_agirecord(path)
    assert dataset.summary()["records"] == 2
    assert len(dataset.shuffle(seed=1).batch(1)) == 2
    split = dataset.split(test_ratio=0.5)
    assert split["train"].summary()["records"] == 1


def test_cnn_batch_training_and_evaluation() -> None:
    dataset = AGIRecordDataset.from_pairs([_image(), _image()], [1, 1])
    model = NativeCNNClassifierV2.create(_kernels(), labels=["low", "high"], feature_count=1, seed=1, pool_size=1)
    history = train_cnn_batches(model, dataset, epochs=2, batch_size=1, learning_rate=0.01)
    assert len(history["loss"]) == 2
    report = evaluate_cnn(model, dataset)
    assert report["samples"] == 2
    assert 0.0 <= report["accuracy"] <= 1.0


def test_tokenizer_transformer_benchmark_and_model_exchange(tmp_path: Path) -> None:
    tok = VocabTokenizer.train_word(["agi lang trains models", "agi lang builds apps"], vocab_size=20)
    ids = tok.encode("agi lang", add_special=True)
    assert ids[0] == tok.token_to_id["<bos>"]
    assert tok.summary()["vocab_size"] >= 4
    stack = transformer_stack(vocab_size=tok.summary()["vocab_size"], dim=8, heads=2, hidden_dim=16, layers=2)
    assert len(stack["blocks"]) == 2
    bench = time_call("tiny", lambda: sum(range(5)), repeats=2)
    assert bench["repeats"] == 2
    assert "onnx_available" in onnx_bridge_status()
    path = tmp_path / "exchange" / "model.json"
    export_descriptor(path, "cnn", {"labels": ["low", "high"]})
    assert path.exists()
