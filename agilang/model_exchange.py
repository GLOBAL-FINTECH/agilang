"""Model exchange bridge for AGILANG AIFlow.

This module reports real production backend availability while keeping the old
descriptor-export utility for lightweight AGILANG models.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

MODEL_EXCHANGE_FORMAT = "agilang-model-exchange-descriptor-v2"


def _available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def onnx_bridge_status() -> dict[str, Any]:
    onnx_available = _available("onnx")
    onnxruntime_available = _available("onnxruntime")
    return {
        "onnx_available": onnx_available,
        "onnxruntime_available": onnxruntime_available,
        "import_supported": "real_onnx_with_onnx_package" if onnx_available else "descriptor_only",
        "execution_supported": "real_onnxruntime" if onnxruntime_available else "descriptor_only",
        "export_supported": "descriptor_only",
        "target_format": ".agi-model",
        "recommended_production_package": "onnxruntime-gpu or onnxruntime",
    }


def export_descriptor(path: str | Path, model_type: str, metadata: dict[str, Any]) -> str:
    payload = {"format": MODEL_EXCHANGE_FORMAT, "model_type": model_type, "metadata": metadata}
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return str(p)


def load_descriptor(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("format") not in {MODEL_EXCHANGE_FORMAT, "agilang-model-exchange-descriptor"}:
        raise ValueError(f"unsupported model descriptor format: {payload.get('format')}")
    return payload


__all__ = ["MODEL_EXCHANGE_FORMAT", "onnx_bridge_status", "export_descriptor", "load_descriptor"]
