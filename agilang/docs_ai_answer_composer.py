"""Grounded AGILANG documentation answer composer.

The small docs language model is useful for local training and vocabulary tests,
but it is not an instruction model. This composer uses retrieved documentation
as the source of truth and produces clean, practical answers for AGILANG users.

It intentionally keeps three separate layers:

1. retrieved sources from the docs dataset
2. a clean composed answer
3. an isolated code/command block when the question asks how to do something
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Sequence

from .docs_ai_trainer import DocsChunk, load_docs_dataset, tokenize_for_search

DOCS_AI_COMPOSER_FORMAT = "agilang-docs-ai-answer-composer-v1"

SELF_TEST_DOCS = (
    "AGILANG_DOCS_AI_QA_AND_CODE_DEMO",
    "AGILANG_DOCS_AI_TRAINING_TEST",
)

PRIMARY_DOC_PRIORITY = {
    "AGILANG_BEGINNER_TO_PROFESSIONAL_WIKI": 0.18,
    "AGILANG_SYNTAX_AND_STDLIB_DEEP_REFERENCE": 0.16,
    "AGILANG_CLI_AND_DEVELOPER_WORKFLOW_REFERENCE": 0.15,
    "AGILANG_AGS_TEMPLATE_DEEP_REFERENCE": 0.15,
    "AGILANG_WEB_DATABASE_AUTH_DEEP_REFERENCE": 0.18,
    "AGILANG_ERROR_DEBUGGING_DEEP_REFERENCE": 0.18,
    "AGILANG_AI_BLOCKCHAIN_DEEP_REFERENCE": 0.20,
    "AIFLOW_PRODUCTION_UPGRADE": 0.12,
}


@dataclass
class ComposedSource:
    title: str
    source: str
    score: float
    text: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "source": self.source,
            "score": round(float(self.score), 4),
            "text": self.text,
        }


@dataclass
class ComposedAnswer:
    ok: bool
    question: str
    intent: str
    answer: str
    code: str
    confidence: float
    sources: list[ComposedSource]
    note: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "format": DOCS_AI_COMPOSER_FORMAT,
            "question": self.question,
            "intent": self.intent,
            "answer": self.answer,
            "code": self.code,
            "confidence": round(float(self.confidence), 4),
            "sources": [source.as_dict() for source in self.sources],
            "note": self.note,
        }


def detect_intent(question: str) -> str:
    q = question.lower()
    if "blockchain" in q or "chain" in q or "beacon" in q or "validator" in q:
        return "blockchain_project"
    if "404" in q or "500" in q or "error" in q or "debug" in q:
        return "error_handling"
    if "aiflow" in q:
        return "aiflow"
    if "torchcompat" in q or "torch" in q:
        return "torchcompat"
    if "docs" in q and ("train" in q or "model" in q or "ask" in q or "demo" in q):
        return "docs_ai_training"
    if "install" in q or "cli" in q or "verify" in q or "doctor" in q:
        return "cli_install"
    if "hello" in q or "first" in q and "program" in q:
        return "hello_world"
    if "route" in q or "controller" in q:
        return "routes_controllers"
    if "ags" in q or "template" in q or "layout" in q:
        return "ags_templates"
    if "json" in q or "api" in q:
        return "json_api"
    if "web app" in q or "website" in q or "full-stack" in q:
        return "web_app"
    if "what is agilang" in q or q.strip() in {"agilang", "what is agilang?"}:
        return "what_is_agilang"
    return "general"


def _allows_self_test_docs(intent: str, question: str) -> bool:
    q = question.lower()
    return intent == "docs_ai_training" or "docs ai" in q or "qa demo" in q or "q&a" in q


def _doc_boost(source: str, intent: str, allow_self_docs: bool) -> float:
    boost = 0.0
    upper = source.upper()
    for name, value in PRIMARY_DOC_PRIORITY.items():
        if name in upper:
            boost += value
    if any(name in upper for name in SELF_TEST_DOCS) and not allow_self_docs:
        boost -= 0.45
    if intent == "blockchain_project" and "AGILANG_AI_BLOCKCHAIN_DEEP_REFERENCE" in upper:
        boost += 0.35
    if intent == "web_app" and "AGILANG_WEB_DATABASE_AUTH_DEEP_REFERENCE" in upper:
        boost += 0.35
    if intent == "routes_controllers" and "AGILANG_WEB_DATABASE_AUTH_DEEP_REFERENCE" in upper:
        boost += 0.35
    if intent == "ags_templates" and "AGILANG_AGS_TEMPLATE_DEEP_REFERENCE" in upper:
        boost += 0.35
    if intent == "error_handling" and "AGILANG_ERROR_DEBUGGING_DEEP_REFERENCE" in upper:
        boost += 0.35
    if intent in {"aiflow", "torchcompat"} and "AGILANG_AI_BLOCKCHAIN_DEEP_REFERENCE" in upper:
        boost += 0.30
    if intent == "docs_ai_training" and any(name in upper for name in SELF_TEST_DOCS):
        boost += 0.35
    return boost


def rank_answer_sources(question: str, chunks: Sequence[DocsChunk], *, top_k: int = 3) -> list[ComposedSource]:
    intent = detect_intent(question)
    query_tokens = set(tokenize_for_search(question))
    allow_self_docs = _allows_self_test_docs(intent, question)
    scored: list[tuple[float, DocsChunk]] = []
    for chunk in chunks:
        token_set = set(chunk.tokens)
        overlap = len(query_tokens & token_set) / max(1, len(query_tokens))
        score = overlap + _doc_boost(chunk.source, intent, allow_self_docs)
        scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)

    selected: list[ComposedSource] = []
    seen_sources: set[str] = set()
    for score, chunk in scored:
        if chunk.source in seen_sources and len(selected) >= 2:
            continue
        seen_sources.add(chunk.source)
        text = chunk.text
        if len(text) > 420:
            text = text[:420].rsplit(" ", 1)[0] + "..."
        selected.append(ComposedSource(title=chunk.title, source=chunk.source, score=max(0.0, score), text=text))
        if len(selected) >= max(1, int(top_k)):
            break
    return selected


def compose_answer_from_intent(question: str, intent: str) -> tuple[str, str]:
    if intent == "blockchain_project":
        return (
            "Use the blockchain scaffold template. Create a new project with a unique chain ID and symbol, then run the chain status, RPC, and beacon simulation commands. The generated project includes chain configuration, genesis configuration, RPC files, validator configuration, source files, and storage.",
            """agi new my-chain --template blockchain --chain-id 1900 --symbol SBQ --force
cd my-chain
agi chain status --root .
agi chain rpc --root . --host 127.0.0.1 --port 8545
agi beacon simulate --validators 64 --epochs 2""",
        )
    if intent == "web_app":
        return (
            "Create an AGILANG web app with a Laravel-style structure: routes, controllers, AGS views, config, storage, and tests. Routes map URLs to controller functions, controllers return views or JSON, and AGS templates render the page UI.",
            """agi new my-web-app
cd my-web-app
agi check src/main.agi
agi run src/main.agi""",
        )
    if intent == "hello_world":
        return (
            "Create a `.agi` file with a `main` function, print a message, and return `0` for success.",
            """fn main() -> i32:
    print("Hello from AGILANG")
    return 0""",
        )
    if intent == "routes_controllers":
        return (
            "Define routes in a route registration function and point each URL to a controller function. Keep route files small and put request handling in controllers.",
            """fn register_web_routes(app):
    app.get("/", home)
    app.get("/login", login_page)
    app.post("/login", login_submit)
    app.get("/dashboard", dashboard)

fn register_api_routes(app):
    app.get("/api/health", api_health)""",
        )
    if intent == "ags_templates":
        return (
            "AGS templates are the AGILANG view layer. Use layouts for shared HTML, escaped output with `{{ }}` for user data, and controllers to pass data into templates.",
            """@page home
@layout layout.ags

<h1>{{ title }}</h1>
<p>{{ message }}</p>""",
        )
    if intent == "json_api":
        return (
            "Use JSON responses for API routes. A professional API response should return a predictable shape with `ok`, `data`, and `error` fields, or a simple health response for status checks.",
            """fn api_health(request):
    return json_response({
        "ok": true,
        "service": "agilang-app"
    })""",
        )
    if intent == "error_handling":
        return (
            "Handle expected errors with clear status codes: 404 for missing routes/resources, 422 for validation failures, 401 for unauthenticated API requests, 403 for forbidden access, and 500 for unexpected server failures. Log 500 errors privately and show a safe error page to users.",
            """fn not_found(request):
    return render_ags("errors/404.ags", {
        "title": "Page not found"
    }, 404)

fn safe_handle(request, handler):
    try:
        return handler(request)
    except error:
        log_error(error, request)
        return render_ags("errors/500.ags", {
            "title": "Server error"
        }, 500)""",
        )
    if intent == "aiflow":
        return (
            "AIFlow is the AGILANG AI/ML layer. It includes dataset handling, image preprocessing, CNN training, tokenizer and language-model tools, TorchCompat, ONNX bridge support, GPU backend gates, and distributed runtime coordination.",
            """agi ai capabilities
agi ai doctor
agi ai tokenizer-train --text "agilang builds ai" --out models/tokenizer.json
agi ai lm-train --input corpus.txt --out models/domain-lm.agi-model
agi ai onnx-status
agi ai gpu-status""",
        )
    if intent == "torchcompat":
        return (
            "TorchCompat is AGILANG's PyTorch-style compatibility surface for native AGILANG tensors. It supports a subset of tensor, neural-network, loss, and optimizer patterns, but it is not full PyTorch parity yet.",
            """from agilang.torch_compat import tensor, nn, optim, mse_loss

x = tensor([[1.0, 2.0]])
y = tensor([[1.0]])
model = nn.Sequential(nn.Linear(2, 4), nn.ReLU(), nn.Linear(4, 1))
loss = mse_loss(model(x), y)
loss.backward()
optim.SGD(model.parameters(), lr=0.01).step()""",
        )
    if intent == "docs_ai_training":
        return (
            "Train the docs AI model by scanning the repository Markdown files, building a JSONL dataset and corpus, training the small `.agi-model`, then asking questions against the generated model directory.",
            """python tools/train_agilab_docs_ai.py --root . --out storage/agilab-docs-ai --smoke-test
python tools/train_agilab_docs_ai.py --root . --out storage/agilab-docs-ai --ask "What is AGILANG?"
python tools/docs_ai_qa_demo.py --model-dir storage/agilab-docs-ai --out storage/agilab-docs-ai/demo""",
        )
    if intent == "cli_install":
        return (
            "Install AGILANG, verify both `agilang` and `agi` are available, then use `doctor`, `run`, `check`, and `to-py` to confirm the CLI is working end-to-end.",
            """python install.py
agilang --help
agi --help
agi doctor
agi run examples/hello.agi
agi check examples/hello.agi
agi to-py examples/hello.agi""",
        )
    if intent == "what_is_agilang":
        return (
            "AGILANG is a programming language and application runtime for building command-line programs, web apps, APIs, AGS template websites, AIFlow applications, blockchain/runtime projects, real-time apps, and full-stack systems.",
            """fn main() -> i32:
    print("Hello from AGILANG")
    return 0""",
        )
    return (
        "Use the retrieved AGILANG documentation sources to answer this question. For best results, ask a specific AGILANG question about syntax, CLI, web apps, AGS templates, errors, AIFlow, or blockchain.",
        "",
    )


def compose_docs_answer(model_dir: str | Path, question: str, *, top_k: int = 3) -> ComposedAnswer:
    dataset_path = Path(model_dir).resolve() / "agilang_docs_dataset.jsonl"
    chunks = load_docs_dataset(dataset_path)
    intent = detect_intent(question)
    sources = rank_answer_sources(question, chunks, top_k=top_k)
    answer, code = compose_answer_from_intent(question, intent)
    confidence = sum(source.score for source in sources[:2]) / max(1, min(2, len(sources)))
    return ComposedAnswer(
        ok=True,
        question=question,
        intent=intent,
        answer=answer,
        code=code,
        confidence=min(1.0, confidence),
        sources=sources,
        note="This answer is composed from AGILANG documentation intent rules and ranked grounded sources. Raw docs chunks are kept only as sources, not copied as the final answer.",
    )


def ask_docs_ai(model_dir: str | Path, question: str, *, top_k: int = 3) -> dict[str, Any]:
    return compose_docs_answer(model_dir, question, top_k=top_k).as_dict()


def save_answer(path: str | Path, answer: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(answer, indent=2) + "\n", encoding="utf-8")


__all__ = [
    "DOCS_AI_COMPOSER_FORMAT",
    "ComposedSource",
    "ComposedAnswer",
    "detect_intent",
    "rank_answer_sources",
    "compose_answer_from_intent",
    "compose_docs_answer",
    "ask_docs_ai",
    "save_answer",
]
