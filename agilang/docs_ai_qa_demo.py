"""AGILANG documentation AI Q&A and code-task demo runner.

This module evaluates a trained AGILANG documentation model by asking practical
questions and code-writing tasks. It saves both JSON and Markdown reports so a
human can inspect whether the docs-trained model retrieves the correct AGILANG
knowledge and produces useful local-model text.

The demo is intentionally honest:
- `grounded_context` comes from the documentation dataset.
- `small_model_generated_text` comes from the trained small language model.
- `reference_solution` is a documentation-grounded expected answer/snippet used
  for checking whether the retrieved context and generated output are useful.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .docs_ai_trainer import answer_question


DEFAULT_QA_QUESTIONS = [
    "What is AGILANG?",
    "How do I install AGILANG and verify the CLI works?",
    "How do I write my first hello world AGI program?",
    "What is the recommended AGILANG full-stack project structure?",
    "How do routes and controllers work in AGILANG web apps?",
    "What are AGS templates used for?",
    "How should AGILANG handle 404 and 500 errors?",
    "How do I create JSON API responses in AGILANG?",
    "What is AIFlow in AGILANG?",
    "What is TorchCompat?",
    "How do I train a small language model using AGILANG docs?",
    "How do I create a blockchain project in AGILANG?",
]


DEFAULT_CODE_TASKS = [
    {
        "task": "Write a hello world AGILANG program.",
        "question": "How do I write a hello world AGI program?",
        "reference_solution": """```agi
fn main() -> i32:
    print("Hello from AGILANG")
    return 0
```""",
        "validation_hint": "Save as hello.agi and run: agi run hello.agi",
    },
    {
        "task": "Write AGILANG routes for home, login, dashboard, and API health.",
        "question": "How do I create AGILANG web routes for home login dashboard and API health?",
        "reference_solution": """```agi
fn register_web_routes(app):
    app.get("/", home)
    app.get("/login", login_page)
    app.post("/login", login_submit)
    app.get("/dashboard", dashboard)

fn register_api_routes(app):
    app.get("/api/health", api_health)
```""",
        "validation_hint": "Confirm each controller function exists and returns a response.",
    },
    {
        "task": "Write an AGS layout and home page with data rendering.",
        "question": "How do I render data in AGS templates with a layout?",
        "reference_solution": """```ags
<!-- resources/views/layout.ags -->
<!doctype html>
<html>
<head>
    <title>{{ title }}</title>
</head>
<body>
    <main>{{ content }}</main>
</body>
</html>
```

```ags
@page home
@layout layout.ags

<h1>{{ title }}</h1>
<p>{{ message }}</p>
```""",
        "validation_hint": "Controller should call render_ags("home.ags", {"title": "Home", "message": "Welcome"}).",
    },
    {
        "task": "Write a protected dashboard controller.",
        "question": "How do I protect an AGILANG dashboard route using sessions?",
        "reference_solution": """```agi
fn dashboard(request):
    let user_id = request.session_get("user_id")
    if user_id == null:
        return redirect("/login")

    return render_ags("dashboard.ags", {
        "title": "Dashboard"
    })
```""",
        "validation_hint": "Guest users should redirect to /login; logged-in users should see dashboard."
    },
    {
        "task": "Write a JSON API health endpoint.",
        "question": "How do I create a JSON API response in AGILANG?",
        "reference_solution": """```agi
fn api_health(request):
    return json_response({
        "ok": true,
        "service": "agilang-app"
    })
```""",
        "validation_hint": "Expected status is 200 with ok=true."
    },
    {
        "task": "Write a custom 404 handler and template.",
        "question": "How do I handle 404 errors in AGILANG?",
        "reference_solution": """```agi
fn not_found(request):
    return render_ags("errors/404.ags", {
        "title": "Page not found"
    }, 404)
```

```ags
@page errors.404
@layout layout.ags

<h1>404 - Page not found</h1>
<p>The page you requested does not exist.</p>
<a href="/">Return home</a>
```""",
        "validation_hint": "Visit a missing route and confirm status 404."
    },
    {
        "task": "Write a safe 500 error wrapper.",
        "question": "How do I collect and handle 500 errors in AGILANG?",
        "reference_solution": """```agi
fn safe_handle(request, handler):
    try:
        return handler(request)
    except error:
        log_error(error, request)
        return render_ags("errors/500.ags", {
            "title": "Server error"
        }, 500)
```""",
        "validation_hint": "Simulate a division-by-zero route and confirm the error is logged."
    },
    {
        "task": "Write commands to train the AGILANG docs AI model.",
        "question": "How do I train a small AGILANG docs AI model from Markdown documentation?",
        "reference_solution": """```powershell
python tools/train_agilab_docs_ai.py --root . --out storage/agilab-docs-ai --smoke-test
python tools/train_agilab_docs_ai.py --root . --out storage/agilab-docs-ai --ask "What is AGILANG?"
python -m pytest tests/test_docs_ai_trainer.py -q
```""",
        "validation_hint": "Expected output includes agilang_docs_dataset.jsonl and agilang_docs_lm.agi-model."
    },
    {
        "task": "Write commands to create an AGILANG blockchain project.",
        "question": "How do I create a blockchain project in AGILANG?",
        "reference_solution": """```powershell
agi new my-chain --template blockchain --chain-id 1900 --symbol SBQ --force
cd my-chain
agi chain status --root .
agi chain rpc --root . --host 127.0.0.1 --port 8545
agi beacon simulate --validators 64 --epochs 2
```""",
        "validation_hint": "Confirm chain config is generated and status command responds."
    },
]


@dataclass
class DemoResult:
    ok: bool
    model_dir: str
    qa_count: int
    code_task_count: int
    json_report_path: str
    markdown_report_path: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _answer(model_dir: str | Path, question: str, *, top_k: int, generate_steps: int) -> dict[str, Any]:
    return answer_question(model_dir, question, top_k=top_k, generate_steps=generate_steps)


def run_qa_demo(
    model_dir: str | Path,
    out_dir: str | Path,
    *,
    questions: list[str] | None = None,
    code_tasks: list[dict[str, str]] | None = None,
    top_k: int = 4,
    generate_steps: int = 32,
) -> dict[str, Any]:
    model_path = Path(model_dir).resolve()
    output = Path(out_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)

    questions = list(questions or DEFAULT_QA_QUESTIONS)
    code_tasks = list(code_tasks or DEFAULT_CODE_TASKS)

    qa_answers = []
    for question in questions:
        qa_answers.append(_answer(model_path, question, top_k=top_k, generate_steps=generate_steps))

    task_answers = []
    for item in code_tasks:
        question = item.get("question") or item["task"]
        answer = _answer(model_path, question, top_k=top_k, generate_steps=generate_steps)
        task_answers.append({
            "task": item["task"],
            "question": question,
            "model_answer": answer,
            "reference_solution": item.get("reference_solution", ""),
            "validation_hint": item.get("validation_hint", ""),
        })

    report = {
        "ok": True,
        "model_dir": str(model_path),
        "answer_mode": "retrieval_plus_small_lm_with_reference_code_tasks",
        "qa_answers": qa_answers,
        "code_tasks": task_answers,
        "note": "Inspect grounded_context first. The small model output is an experimental local language-model continuation, while reference_solution is the expected docs-grounded answer.",
    }

    json_path = output / "agilang_docs_ai_qa_demo.json"
    md_path = output / "agilang_docs_ai_qa_demo.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown_report(report), encoding="utf-8")

    result = DemoResult(
        ok=True,
        model_dir=str(model_path),
        qa_count=len(qa_answers),
        code_task_count=len(task_answers),
        json_report_path=str(json_path),
        markdown_report_path=str(md_path),
    )
    return {"summary": result.as_dict(), "report": report}


def render_markdown_report(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# AGILANG Docs AI Q&A and Code Task Demo")
    lines.append("")
    lines.append(f"Model directory: `{report['model_dir']}`")
    lines.append("")
    lines.append("> Read `grounded_context` first. The local small model is useful for vocabulary/pattern testing, not GPT-level reasoning.")
    lines.append("")

    lines.append("## Q&A Results")
    lines.append("")
    for idx, answer in enumerate(report["qa_answers"], start=1):
        lines.append(f"### {idx}. {answer['question']}")
        lines.append("")
        lines.append("**Grounded documentation context:**")
        lines.append("")
        for context in answer.get("grounded_context", [])[:3]:
            lines.append(f"- `{context['source']}` score={context['score']:.3f}: {context['text']}")
        lines.append("")
        lines.append("**Small model generated text:**")
        lines.append("")
        lines.append("```text")
        lines.append(str(answer.get("small_model_generated_text", "")))
        lines.append("```")
        lines.append("")

    lines.append("## Code Writing Task Results")
    lines.append("")
    for idx, item in enumerate(report["code_tasks"], start=1):
        answer = item["model_answer"]
        lines.append(f"### Task {idx}. {item['task']}")
        lines.append("")
        lines.append(f"Question asked: `{item['question']}`")
        lines.append("")
        lines.append("**Grounded documentation context:**")
        lines.append("")
        for context in answer.get("grounded_context", [])[:3]:
            lines.append(f"- `{context['source']}` score={context['score']:.3f}: {context['text']}")
        lines.append("")
        lines.append("**Small model generated text:**")
        lines.append("")
        lines.append("```text")
        lines.append(str(answer.get("small_model_generated_text", "")))
        lines.append("```")
        lines.append("")
        lines.append("**Reference solution:**")
        lines.append("")
        lines.append(item.get("reference_solution", ""))
        lines.append("")
        if item.get("validation_hint"):
            lines.append(f"Validation hint: {item['validation_hint']}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


__all__ = [
    "DEFAULT_QA_QUESTIONS",
    "DEFAULT_CODE_TASKS",
    "DemoResult",
    "run_qa_demo",
    "render_markdown_report",
]
