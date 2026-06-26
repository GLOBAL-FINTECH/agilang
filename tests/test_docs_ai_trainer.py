from __future__ import annotations

from pathlib import Path

from agilang.docs_ai_trainer import answer_question, build_docs_dataset, find_markdown_files, run_training_smoke_test, train_docs_model


def test_find_markdown_files_and_build_dataset(tmp_path):
    (tmp_path / "README.md").write_text("# AGILANG\n\nAGILANG is a programming language for web apps, AIFlow, and blockchain.\n", encoding="utf-8")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "AI.md").write_text("# AIFlow\n\nAIFlow trains tokenizers, language models, and CNN models.\n", encoding="utf-8")

    files = find_markdown_files(tmp_path)
    assert len(files) == 2

    summary = build_docs_dataset(tmp_path, tmp_path / "out", max_words=30)
    assert summary["markdown_files"] == 2
    assert summary["chunks"] >= 2
    assert Path(summary["dataset_path"]).exists()
    assert Path(summary["corpus_path"]).exists()


def test_train_docs_model_and_answer_question(tmp_path):
    (tmp_path / "README.md").write_text(
        "# AGILANG\n\nAGILANG is a programming language and runtime for web apps, APIs, AIFlow, and blockchain projects.\n",
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "WEB.md").write_text(
        "# AGILANG Web\n\nAGILANG web apps use routes, controllers, AGS templates, forms, sessions, and JSON APIs.\n",
        encoding="utf-8",
    )
    (docs / "AI.md").write_text(
        "# AGILANG AIFlow\n\nAIFlow includes BPE tokenizers, small language models, TorchCompat, ONNX bridges, and image preprocessing.\n",
        encoding="utf-8",
    )

    result = train_docs_model(tmp_path, tmp_path / "model", merges=40, order=2, max_words=40)
    assert result.ok is True
    assert Path(result.dataset_path).exists()
    assert Path(result.model_path).exists()

    answer = answer_question(result.out_dir, "What is AIFlow?", top_k=2, generate_steps=8)
    assert answer["ok"] is True
    assert answer["grounded_context"]
    joined = " ".join(item["text"].lower() for item in answer["grounded_context"])
    assert "aiflow" in joined


def test_run_training_smoke_test(tmp_path):
    (tmp_path / "README.md").write_text(
        "# AGILANG\n\nAGILANG teaches full-stack development with syntax, routes, templates, AIFlow, and blockchain.\n",
        encoding="utf-8",
    )
    report = run_training_smoke_test(tmp_path, tmp_path / "smoke")
    assert report["ok"] is True
    assert report["training"]["chunks"] >= 1
    assert report["answers"]
    assert Path(tmp_path / "smoke" / "smoke_test_answers.json").exists()
