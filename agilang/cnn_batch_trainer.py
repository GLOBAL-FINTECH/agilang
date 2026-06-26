"""Batch training helpers for AGILANG native CNN classifier."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from .agirecord import AGIRecordDataset
from .cnn_training_loop_v2 import NativeCNNClassifierV2


def train_cnn_batches(
    model: NativeCNNClassifierV2,
    dataset: AGIRecordDataset,
    *,
    epochs: int = 1,
    batch_size: int = 4,
    learning_rate: float = 0.001,
    shuffle: bool = True,
) -> dict[str, list[float]]:
    history = {"loss": []}
    data = dataset
    for epoch in range(epochs):
        if shuffle:
            data = dataset.shuffle(seed=epoch + 1)
        total = 0.0
        count = 0
        for batch in data.batch(batch_size):
            for record in batch:
                result = model.train_step(record.features, int(record.label), learning_rate=learning_rate)
                total += float(result["loss"])
                count += 1
        history["loss"].append(total / max(1, count))
    return history


def evaluate_cnn(model: NativeCNNClassifierV2, dataset: AGIRecordDataset) -> dict[str, Any]:
    total = 0
    correct = 0
    for record in dataset.records:
        pred = model.predict(record.features)
        total += 1
        correct += 1 if int(pred["predicted_index"]) == int(record.label) else 0
    return {"samples": total, "correct": correct, "accuracy": correct / max(1, total)}


def save_checkpoint(model: NativeCNNClassifierV2, directory: str | Path, epoch: int) -> str:
    path = Path(directory) / f"cnn_epoch_{int(epoch)}.agi-model"
    return model.save(path)


__all__ = ["train_cnn_batches", "evaluate_cnn", "save_checkpoint"]
