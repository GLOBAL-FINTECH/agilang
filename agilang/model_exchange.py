"""Model exchange bridge descriptors for AGILANG AIFlow."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def onnx_bridge_status() -> dict[str, Any]:
    try:
        import onnx  # type: ignore  # noqa: F401
        available = True
    except Exception:
        available = False
    return {"onnx_available": available, "import_supported": "descriptor_only", "export_supported": "descriptor_only", "target_format": ".agi-model"}


def export_descriptor(path: str | Path, model_type: str, metadata: dict[str, Any]) -> str:
    import json
    payload = {"format": "agilang-model-exchange-descriptor", "model_type": model_type, "metadata": metadata}
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(p)


__all__ = ["onnx_bridge_status", "export_descriptor"]
