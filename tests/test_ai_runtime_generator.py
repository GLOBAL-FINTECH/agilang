from __future__ import annotations

from pathlib import Path

from agilang.ai_runtime_generator import generate_ai_runtime_app


def test_ai_runtime_generator_creates_agi_entrypoints_only(tmp_path: Path) -> None:
    result = generate_ai_runtime_app("Demo AI", tmp_path, force=True)
    root = Path(result["root"])
    assert result["python_launchers"] is False
    for name in ["run.agi", "dataset.agi", "train.agi", "infer.agi", "cnn.agi", "llm.agi", "onnx.agi", "gpu.agi", "distributed.agi", "benchmark.agi", "transformer.agi"]:
        assert (root / name).exists()
    assert not (root / "run.py").exists()
    assert not (root / "train.py").exists()
    assert not (root / "infer.py").exists()
    assert (root / "src" / "cnn.agi").exists()
    assert (root / "resources" / "views" / "dashboard.ags").exists()


def test_ai_runtime_generator_config_declares_no_python_launchers(tmp_path: Path) -> None:
    result = generate_ai_runtime_app("AI Config", tmp_path, force=True)
    root = Path(result["root"])
    config = (root / "config" / "ai.json").read_text(encoding="utf-8")
    assert '"python_launchers": false' in config
    toml = (root / "agilang.toml").read_text(encoding="utf-8")
    assert "generated_python_launchers = false" in toml
