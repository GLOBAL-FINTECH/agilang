"""AGI-native AI runtime project generator.

The generated project exposes AGILANG entrypoints only: run.agi, train.agi,
infer.agi, dataset.agi, benchmark.agi, and transformer.agi. No Python launcher
files are generated for the application surface.
"""
from __future__ import annotations

import json
import shutil
import textwrap
from pathlib import Path
from typing import Any


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")


def _safe_name(name: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in name.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "ai-app"


def generate_ai_runtime_app(name: str, root_dir: str | Path = ".", *, force: bool = False, vendor: bool = True) -> dict[str, Any]:
    project = Path(root_dir).resolve() / _safe_name(name)
    if project.exists():
        if not force:
            raise FileExistsError(f"project already exists: {project}")
        shutil.rmtree(project)
    project.mkdir(parents=True)

    _write(project / "agilang.toml", f'''
        [app]
        name = "{name}"
        type = "ai-runtime"
        entry = "run.agi"

        [runtime]
        language = "agi"
        templates = "ags"
        generated_python_launchers = false
    ''')
    _write(project / ".env.example", '''
        APP_NAME="AGILANG AI Runtime"
        APP_ENV=local
        APP_DEBUG=true
        DATASET_PATH=storage/datasets/demo.agi-record
        MODEL_PATH=storage/models/demo.agi-model
        AI_BACKEND=cpu_reference
    ''')
    _write(project / "run.agi", '''
        fn main() -> i32:
            print("AGILANG AI Runtime")
            print("Commands: agi run train.agi | agi run infer.agi | agi run dataset.agi | agi run benchmark.agi | agi run transformer.agi")
            return include("src/ai_runtime.agi")
    ''')
    _write(project / "train.agi", '''
        fn main() -> i32:
            print("AGILANG AI training workflow")
            print("Pipeline: AGIRecord -> CNN trainer -> model checkpoint")
            return include("src/train.agi")
    ''')
    _write(project / "infer.agi", '''
        fn main() -> i32:
            print("AGILANG AI inference workflow")
            print("Pipeline: image/text input -> model -> prediction")
            return include("src/infer.agi")
    ''')
    _write(project / "dataset.agi", '''
        fn main() -> i32:
            print("AGILANG dataset workflow")
            print("Pipeline: records -> AGIRecord -> indexed AGIRecord -> batches")
            return include("src/dataset.agi")
    ''')
    _write(project / "benchmark.agi", '''
        fn main() -> i32:
            print("AGILANG benchmark workflow")
            print("Pipeline: reference kernel -> timed run -> report")
            return include("src/benchmark.agi")
    ''')
    _write(project / "transformer.agi", '''
        fn main() -> i32:
            print("AGILANG transformer workflow")
            print("Pipeline: tokenizer -> attention -> transformer block -> tiny LM")
            return include("src/transformer.agi")
    ''')

    _write(project / "src" / "ai_runtime.agi", '''
        fn main() -> i32:
            print("AIFlow modules enabled: dataset, CNN, tokenizer, transformer, ONNX reference, distributed planner, GPU planner")
            return 0
    ''')
    _write(project / "src" / "train.agi", '''
        fn main() -> i32:
            print("Training example")
            print("Use AGIRecord data from storage/datasets and save .agi-model checkpoints into storage/models")
            return 0
    ''')
    _write(project / "src" / "infer.agi", '''
        fn main() -> i32:
            print("Inference example")
            print("Load .agi-model, run prediction, return label/probability")
            return 0
    ''')
    _write(project / "src" / "dataset.agi", '''
        fn main() -> i32:
            print("Dataset example")
            print("Create AGIRecord, shuffle, batch, split, index")
            return 0
    ''')
    _write(project / "src" / "benchmark.agi", '''
        fn main() -> i32:
            print("Benchmark example")
            print("Run reference CPU kernel timing and compare later with GPU kernels")
            return 0
    ''')
    _write(project / "src" / "transformer.agi", '''
        fn main() -> i32:
            print("Transformer example")
            print("Tokenize text, run attention, train tiny language model")
            return 0
    ''')
    _write(project / "resources" / "views" / "dashboard.ags", '''
        <main class="ai-dashboard">
          <h1>AGILANG AI Runtime</h1>
          <p>Native AGI project surface for AIFlow training and inference.</p>
        </main>
    ''')
    _write(project / "config" / "ai.json", json.dumps({
        "backend": "cpu_reference",
        "dataset": "storage/datasets/demo.agi-record",
        "model": "storage/models/demo.agi-model",
        "generated_entrypoints": ["run.agi", "train.agi", "infer.agi", "dataset.agi", "benchmark.agi", "transformer.agi"],
        "python_launchers": False,
    }, indent=2))
    (project / "storage" / "datasets").mkdir(parents=True, exist_ok=True)
    (project / "storage" / "models").mkdir(parents=True, exist_ok=True)
    _write(project / "README.md", '''
        # AGILANG AI Runtime App

        This project is generated with AGILANG entrypoints only.

        ```bash
        agi run run.agi
        agi run dataset.agi
        agi run train.agi
        agi run infer.agi
        agi run benchmark.agi
        agi run transformer.agi
        ```

        The app-facing runtime files are `.agi`. The current AGILANG implementation may still use the vendored runtime internally, but generated application entrypoints are not Python launchers.
    ''')
    return {"ok": True, "root": str(project), "entrypoints": ["run.agi", "train.agi", "infer.agi", "dataset.agi", "benchmark.agi", "transformer.agi"], "python_launchers": False}


__all__ = ["generate_ai_runtime_app"]
