"""AGI-native AI runtime project generator.

Generated AI runtime apps expose AGILANG source entrypoints only. No Python
launcher files are created for the application surface. Python may still be used
internally by the current AGILANG runtime package until native/C/GPU runtimes
mature, but user-facing app code is `.agi` and `.ags`.
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
    return cleaned.strip("-") or "ai-runtime"


def generate_ai_runtime_app(name: str, root_dir: str | Path = ".", *, force: bool = False, vendor: bool = True) -> dict[str, Any]:
    project_name = _safe_name(name)
    project = Path(root_dir).resolve() / project_name
    if project.exists():
        if not force:
            raise FileExistsError(f"project already exists: {project}")
        shutil.rmtree(project)
    project.mkdir(parents=True)

    entrypoints = [
        "run.agi",
        "dataset.agi",
        "train.agi",
        "infer.agi",
        "cnn.agi",
        "llm.agi",
        "onnx.agi",
        "gpu.agi",
        "distributed.agi",
        "benchmark.agi",
        "transformer.agi",
    ]

    _write(project / "agilang.toml", f'''
        [app]
        name = "{project_name}"
        type = "ai-runtime"
        entry = "run.agi"

        [runtime]
        language = "agi"
        templates = "ags"
        generated_python_launchers = false

        [ai]
        runtime = "aiflow"
        dataset_format = "agirecord"
        indexed_dataset_format = "agirecord-index-v2"
        model_format = ".agi-model"
        default_backend = "cpu_reference"
    ''')
    _write(project / ".env.example", '''
        APP_NAME="AGILANG AI Runtime"
        APP_ENV=local
        APP_DEBUG=true
        DATASET_PATH=storage/datasets/demo.agi-record
        MODEL_PATH=storage/models/demo.agi-model
        CHECKPOINT_PATH=storage/checkpoints
        AI_BACKEND=cpu_reference
    ''')

    root_map = {
        "run.agi": "src/ai_runtime.agi",
        "dataset.agi": "src/dataset.agi",
        "train.agi": "src/train.agi",
        "infer.agi": "src/infer.agi",
        "cnn.agi": "src/cnn.agi",
        "llm.agi": "src/llm.agi",
        "onnx.agi": "src/onnx.agi",
        "gpu.agi": "src/gpu.agi",
        "distributed.agi": "src/distributed.agi",
        "benchmark.agi": "src/benchmark.agi",
        "transformer.agi": "src/transformer.agi",
    }
    for entry, target in root_map.items():
        _write(project / entry, f'''
            fn main() -> i32:
                print("AGILANG AI runtime entry", "{entry}")
                return include("{target}")
        ''')

    _write(project / "config" / "ai.agi", '''
        fn ai_config():
            return {
                "runtime": "aiflow",
                "dataset_format": "agirecord",
                "indexed_dataset_format": "agirecord-index-v2",
                "model_format": ".agi-model",
                "backend": env("AI_BACKEND", "cpu_reference"),
                "dataset": env("DATASET_PATH", "storage/datasets/demo.agi-record"),
                "model": env("MODEL_PATH", "storage/models/demo.agi-model"),
                "checkpoints": env("CHECKPOINT_PATH", "storage/checkpoints")
            }
    ''')
    _write(project / "routes" / "ai.agi", '''
        fn ai_routes():
            return [
                {"method": "GET", "path": "/ai/status", "handler": "AiController.status"},
                {"method": "POST", "path": "/ai/train", "handler": "AiController.train"},
                {"method": "POST", "path": "/ai/infer", "handler": "AiController.infer"}
            ]
    ''')
    _write(project / "app" / "controllers" / "AiController.agi", '''
        fn status(request):
            return json_response({"ok": true, "runtime": "AGILANG AIFlow", "backend": "cpu_reference"})

        fn train(request):
            return json_response({"ok": true, "message": "Training workflow is defined in train.agi"})

        fn infer(request):
            return json_response({"ok": true, "message": "Inference workflow is defined in infer.agi"})
    ''')

    source_files = {
        "ai_runtime.agi": '''
            fn main() -> i32:
                print("AGILANG AIFlow Runtime")
                print("Use AGI commands only:")
                print("agi run dataset.agi")
                print("agi run train.agi")
                print("agi run infer.agi")
                print("agi run cnn.agi")
                print("agi run llm.agi")
                print("agi run onnx.agi")
                print("agi run gpu.agi")
                print("agi run distributed.agi")
                return 0
        ''',
        "dataset.agi": '''
            fn main() -> i32:
                print("Dataset workflow")
                print("AGIRecord save/load -> Indexed AGIRecord random access -> shuffle -> batch -> split")
                return 0
        ''',
        "train.agi": '''
            fn main() -> i32:
                print("Training workflow")
                print("AGIRecord -> CNN batch trainer -> evaluation -> checkpoint -> .agi-model")
                return 0
        ''',
        "infer.agi": '''
            fn main() -> i32:
                print("Inference workflow")
                print("Load .agi-model -> run predict -> return label/probability")
                return 0
        ''',
        "cnn.agi": '''
            fn main() -> i32:
                print("CNN workflow")
                print("RGB image -> Conv2D -> ReLU -> MaxPool -> Flatten -> Dense -> Softmax")
                print("Backward: Dense -> MaxPool -> ReLU -> Conv2D -> Adam")
                return 0
        ''',
        "llm.agi": '''
            fn main() -> i32:
                print("LLM workflow")
                print("Text -> BPE tokenizer -> token pairs -> tiny LM trainer -> .agi-model")
                return 0
        ''',
        "onnx.agi": '''
            fn main() -> i32:
                print("ONNX Tier 1 reference workflow")
                print("Ops: Relu, Sigmoid, Softmax, MatMul, Add, Mul, Flatten, Reshape, Transpose, Gemm")
                return 0
        ''',
        "gpu.agi": '''
            fn main() -> i32:
                print("GPU runtime workflow")
                print("Backends: CUDA, ROCm, DirectML, Metal, CPU fallback")
                print("Status: registry and planner ready; hardware kernels remain production-hardening work")
                return 0
        ''',
        "distributed.agi": '''
            fn main() -> i32:
                print("Distributed workflow")
                print("Local reference: shard planning + allreduce_average")
                print("Future: real worker transport and multi-node execution")
                return 0
        ''',
        "benchmark.agi": '''
            fn main() -> i32:
                print("Benchmark workflow")
                print("Reference kernel timing -> compare against NumPy/PyTorch/TensorFlow later")
                return 0
        ''',
        "transformer.agi": '''
            fn main() -> i32:
                print("Transformer workflow")
                print("LayerNorm -> attention -> feed-forward -> transformer block")
                return 0
        ''',
    }
    for filename, content in source_files.items():
        _write(project / "src" / filename, content)

    _write(project / "resources" / "views" / "dashboard.ags", '''
        <main class="ai-dashboard">
          <section class="hero">
            <h1>AGILANG AIFlow Runtime</h1>
            <p>Train, evaluate, infer, tokenize, benchmark, and plan deployment from AGI files.</p>
          </section>
        </main>
    ''')
    _write(project / "config" / "ai.json", json.dumps({
        "backend": "cpu_reference",
        "dataset": "storage/datasets/demo.agi-record",
        "model": "storage/models/demo.agi-model",
        "checkpoints": "storage/checkpoints",
        "generated_entrypoints": entrypoints,
        "python_launchers": False,
    }, indent=2))

    (project / "storage" / "datasets").mkdir(parents=True, exist_ok=True)
    (project / "storage" / "models").mkdir(parents=True, exist_ok=True)
    (project / "storage" / "checkpoints").mkdir(parents=True, exist_ok=True)

    _write(project / "README.md", f'''
        # {project_name} — AGILANG AI Runtime App

        This project is generated with AGILANG entrypoints only.

        ```bash
        agi run run.agi
        agi run dataset.agi
        agi run train.agi
        agi run infer.agi
        agi run cnn.agi
        agi run llm.agi
        agi run onnx.agi
        agi run gpu.agi
        agi run distributed.agi
        agi run benchmark.agi
        agi run transformer.agi
        ```

        The app-facing runtime files are `.agi`. No `run.py`, `train.py`, or Python launcher files are generated for the application surface.
    ''')
    return {"ok": True, "root": str(project), "entrypoints": entrypoints, "python_launchers": False}


__all__ = ["generate_ai_runtime_app"]
