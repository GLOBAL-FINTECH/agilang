from __future__ import annotations

from pathlib import Path

from agilang.agirecord import AGIRecord
from agilang.agirecord_indexed import IndexedAGIRecord
from agilang.bpe_tokenizer import BPETokenizer
from agilang.distributed_training import TrainingNode, distributed_plan
from agilang.gpu_runtime_plan import detect_gpu_backends, select_accelerator
from agilang.image_ops import crop_center, flip_left_right, pixel_scale, resize_nearest
from agilang.transformer_runtime import attention_scores, layer_norm, transformer_block


def test_image_ops() -> None:
    image = [[0, 255], [128, 64]]
    assert pixel_scale([[0, 255]]) == [[0.0, 1.0]]
    assert flip_left_right(image) == [[255, 0], [64, 128]]
    assert crop_center([[1, 2, 3], [4, 5, 6], [7, 8, 9]], 1, 1) == [[5]]
    assert resize_nearest([[1, 2], [3, 4]], 1, 1) == [[1]]


def test_indexed_agirecord_random_access(tmp_path: Path) -> None:
    records = [AGIRecord([1], 0), AGIRecord([2], 1)]
    indexed = IndexedAGIRecord.write(tmp_path / "data.agi-record", records)
    opened = IndexedAGIRecord.open(indexed.data_path)
    assert len(opened) == 2
    assert opened.get(1).label == 1
    assert opened.summary()["records"] == 2


def test_bpe_transformer_gpu_and_distributed_planners() -> None:
    tok = BPETokenizer.train(["agi lang trains", "agi lang runs"], merges=5)
    assert tok.summary()["merges"] <= 5
    assert tok.encode("agi lang")
    scores = attention_scores([1, 0], [[1, 0], [0, 1]])
    assert round(sum(scores), 6) == 1.0
    assert len(layer_norm([1, 2, 3])) == 3
    assert len(transformer_block([[1, 0], [0, 1]])) == 2
    assert "cpu" in detect_gpu_backends()
    assert select_accelerator()["backend"] in {"cpu", "cuda", "rocm", "directml", "metal"}
    plan = distributed_plan([TrainingNode("n1", "127.0.0.1", gpus=1)])
    assert plan["total_gpus"] == 1
