from __future__ import annotations

from pathlib import Path

from agilang.docs_ai_qa_demo import DEFAULT_CODE_TASKS, DEFAULT_QA_QUESTIONS, render_markdown_report, run_qa_demo
from agilang.docs_ai_trainer import train_docs_model


def test_docs_ai_qa_demo_generates_json_and_markdown_reports(tmp_path):
    (tmp_path / "README.md").write_text(
        "# AGILANG\n\nAGILANG is a programming language for web apps, APIs, AGS templates, AIFlow, and blockchain.\n"
        "## Hello\n\nA hello program uses fn main, print, and return 0.\n",
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "WEB.md").write_text(
        "# AGILANG Web\n\nRoutes map URLs to controllers. Controllers render AGS templates or return JSON responses.\n",
        encoding="utf-8",
    )
    (docs / "ERRORS.md").write_text(
        "# AGILANG Errors\n\nA 404 means not found. A 500 means server error. Use custom templates and logging.\n",
        encoding="utf-8",
    )

    trained = train_docs_model(tmp_path, tmp_path / "model", merges=50, order=2, max_words=50)
    result = run_qa_demo(trained.out_dir, tmp_path / "demo", questions=DEFAULT_QA_QUESTIONS[:2], code_tasks=DEFAULT_CODE_TASKS[:2])

    summary = result["summary"]
    assert summary["ok"] is True
    assert summary["qa_count"] == 2
    assert summary["code_task_count"] == 2
    assert Path(summary["json_report_path"]).exists()
    assert Path(summary["markdown_report_path"]).exists()

    markdown = Path(summary["markdown_report_path"]).read_text(encoding="utf-8")
    assert "Q&A Results" in markdown
    assert "Code Writing Task Results" in markdown
    assert "Reference solution" in markdown
    assert "fn main" in markdown


def test_render_markdown_report_contains_grounded_context_and_model_text():
    report = {
        "model_dir": "storage/agilab-docs-ai",
        "qa_answers": [
            {
                "question": "What is AGILANG?",
                "grounded_context": [{"source": "README.md", "score": 1.0, "text": "AGILANG is a programming language."}],
                "small_model_generated_text": "AGILANG is a programming language",
            }
        ],
        "code_tasks": [
            {
                "task": "Write hello world",
                "question": "How do I write hello?",
                "model_answer": {
                    "grounded_context": [{"source": "README.md", "score": 1.0, "text": "Use fn main."}],
                    "small_model_generated_text": "fn main print",
                },
                "reference_solution": "```agi\nfn main() -> i32:\n    return 0\n```",
                "validation_hint": "Run agi run hello.agi",
            }
        ],
    }
    markdown = render_markdown_report(report)
    assert "What is AGILANG?" in markdown
    assert "Write hello world" in markdown
    assert "Run agi run hello.agi" in markdown
