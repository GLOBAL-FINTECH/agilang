"""Train and test a small AGILANG documentation AI model.

This module turns repository Markdown documentation into a local AIFlow training
corpus, trains a small tokenizer-backed language model, and provides a simple
retrieval-assisted answer function so developers can test whether the model has
learned the AGILANG documentation vocabulary and concepts.

The trained language model is intentionally small. The retrieval layer is what
makes answers grounded in the documentation instead of hallucinated.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Sequence

from .llm_trainer import LanguageModelBundle, train_ngram_lm, load_language_model

DOCS_AI_FORMAT = "agilang-docs-ai-dataset-v1"
DEFAULT_EXCLUDES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "storage",
    "dist",
    "build",
}


@dataclass
class DocsChunk:
    id: str
    source: str
    title: str
    text: str
    tokens: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "text": self.text,
            "tokens": self.tokens,
        }


@dataclass
class DocsTrainingResult:
    ok: bool
    root: str
    out_dir: str
    markdown_files: int
    chunks: int
    corpus_path: str
    dataset_path: str
    model_path: str
    summary_path: str
    sample_questions_path: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _is_excluded(path: Path) -> bool:
    return any(part in DEFAULT_EXCLUDES for part in path.parts)


def find_markdown_files(root: str | Path, *, include_readme: bool = True) -> list[Path]:
    root_path = Path(root).resolve()
    files: list[Path] = []
    for path in root_path.rglob("*.md"):
        if _is_excluded(path.relative_to(root_path)):
            continue
        if not include_readme and path.name.lower() == "readme.md":
            continue
        files.append(path)
    return sorted(files)


def clean_markdown(text: str) -> str:
    # Keep code content, but remove noisy markdown syntax enough for small LM training.
    text = re.sub(r"```[a-zA-Z0-9_-]*", "\n", text)
    text = text.replace("```", "\n")
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    text = re.sub(r"[`*_>#|]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_title(path: Path, text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or path.stem
    return path.stem.replace("_", " ").replace("-", " ")


def tokenize_for_search(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9_./:-]+", text.lower()) if len(token) > 1]


def chunk_text(text: str, *, max_words: int = 120, overlap: int = 24) -> list[str]:
    words = text.split()
    if not words:
        return []
    max_words = max(20, int(max_words))
    overlap = max(0, min(int(overlap), max_words // 2))
    chunks: list[str] = []
    index = 0
    while index < len(words):
        part = words[index:index + max_words]
        if part:
            chunks.append(" ".join(part))
        if index + max_words >= len(words):
            break
        index += max_words - overlap
    return chunks


def build_docs_dataset(root: str | Path, out_dir: str | Path, *, max_words: int = 120, overlap: int = 24) -> dict[str, Any]:
    root_path = Path(root).resolve()
    output = Path(out_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)

    files = find_markdown_files(root_path)
    chunks: list[DocsChunk] = []
    corpus_lines: list[str] = []

    for path in files:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        title = extract_title(path, raw)
        cleaned = clean_markdown(raw)
        rel = str(path.relative_to(root_path)).replace("\\", "/")
        for idx, chunk in enumerate(chunk_text(cleaned, max_words=max_words, overlap=overlap)):
            chunk_id = f"{rel}#{idx}"
            record = DocsChunk(
                id=chunk_id,
                source=rel,
                title=title,
                text=chunk,
                tokens=tokenize_for_search(title + " " + rel + " " + chunk),
            )
            chunks.append(record)
            corpus_lines.append(f"{title}. Source {rel}. {chunk}")

    dataset_path = output / "agilang_docs_dataset.jsonl"
    corpus_path = output / "agilang_docs_corpus.txt"
    summary_path = output / "agilang_docs_dataset_summary.json"

    with dataset_path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps({"format": DOCS_AI_FORMAT, **chunk.as_dict()}, ensure_ascii=False) + "\n")

    corpus_path.write_text("\n".join(corpus_lines) + ("\n" if corpus_lines else ""), encoding="utf-8")

    summary = {
        "format": DOCS_AI_FORMAT,
        "root": str(root_path),
        "markdown_files": len(files),
        "chunks": len(chunks),
        "dataset_path": str(dataset_path),
        "corpus_path": str(corpus_path),
        "sources": [str(path.relative_to(root_path)).replace("\\", "/") for path in files],
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def load_docs_dataset(dataset_path: str | Path) -> list[DocsChunk]:
    chunks: list[DocsChunk] = []
    with Path(dataset_path).open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            payload = json.loads(line)
            chunks.append(DocsChunk(
                id=str(payload["id"]),
                source=str(payload["source"]),
                title=str(payload.get("title") or payload["source"]),
                text=str(payload["text"]),
                tokens=list(payload.get("tokens") or tokenize_for_search(payload["text"])),
            ))
    return chunks


def train_docs_model(root: str | Path, out_dir: str | Path, *, merges: int = 300, order: int = 3, max_words: int = 120) -> DocsTrainingResult:
    output = Path(out_dir).resolve()
    dataset_summary = build_docs_dataset(root, output, max_words=max_words)
    corpus_path = Path(dataset_summary["corpus_path"])
    texts = [line.strip() for line in corpus_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not texts:
        raise ValueError("No Markdown documentation text found for training")

    bundle = train_ngram_lm(texts, merges=merges, order=order, lowercase=True)
    model_path = output / "agilang_docs_lm.agi-model"
    bundle.save(model_path)

    sample_questions = [
        "What is AGILANG?",
        "How do I create an AGILANG web app?",
        "How does AGILANG handle 404 and 500 errors?",
        "What is AIFlow?",
        "How do I create a blockchain project in AGILANG?",
        "What is TorchCompat?",
    ]
    sample_path = output / "sample_questions.json"
    sample_path.write_text(json.dumps(sample_questions, indent=2) + "\n", encoding="utf-8")

    summary_path = output / "training_summary.json"
    result = DocsTrainingResult(
        ok=True,
        root=str(Path(root).resolve()),
        out_dir=str(output),
        markdown_files=int(dataset_summary["markdown_files"]),
        chunks=int(dataset_summary["chunks"]),
        corpus_path=str(corpus_path),
        dataset_path=str(output / "agilang_docs_dataset.jsonl"),
        model_path=str(model_path),
        summary_path=str(summary_path),
        sample_questions_path=str(sample_path),
    )
    summary_path.write_text(json.dumps(result.as_dict(), indent=2) + "\n", encoding="utf-8")
    return result


def rank_chunks(question: str, chunks: Sequence[DocsChunk], *, top_k: int = 4) -> list[dict[str, Any]]:
    query_tokens = set(tokenize_for_search(question))
    scored: list[tuple[float, DocsChunk]] = []
    for chunk in chunks:
        token_set = set(chunk.tokens)
        overlap = len(query_tokens & token_set)
        if overlap == 0:
            # weak fallback: prefer AGILANG/AIFlow docs if no exact overlap
            overlap = 1 if any(term in token_set for term in ["agilang", "aiflow", "blockchain", "template"]) else 0
        score = overlap / max(1, len(query_tokens))
        scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "score": score,
            "id": chunk.id,
            "source": chunk.source,
            "title": chunk.title,
            "text": chunk.text,
        }
        for score, chunk in scored[: max(1, int(top_k))]
    ]


def answer_question(model_dir: str | Path, question: str, *, top_k: int = 4, generate_steps: int = 24) -> dict[str, Any]:
    model_root = Path(model_dir).resolve()
    dataset_path = model_root / "agilang_docs_dataset.jsonl"
    model_path = model_root / "agilang_docs_lm.agi-model"
    chunks = load_docs_dataset(dataset_path)
    bundle = load_language_model(model_path)
    contexts = rank_chunks(question, chunks, top_k=top_k)
    prompt = f"Question: {question}. Answer about AGILANG:"
    generated = bundle.generate(prompt, steps=generate_steps)

    # The grounded answer uses retrieved documentation first and includes the small
    # LM continuation as an experimental signal, not as sole truth.
    grounded_points = []
    for item in contexts:
        text = item["text"]
        if len(text) > 360:
            text = text[:360].rsplit(" ", 1)[0] + "..."
        grounded_points.append({"source": item["source"], "title": item["title"], "text": text, "score": item["score"]})

    return {
        "ok": True,
        "question": question,
        "answer_mode": "retrieval_plus_small_lm",
        "grounded_context": grounded_points,
        "small_model_generated_text": generated,
        "note": "For proper answers, trust grounded_context first. The small n-gram LM is a local training test, not a large instruction model.",
    }


def run_training_smoke_test(root: str | Path, out_dir: str | Path) -> dict[str, Any]:
    result = train_docs_model(root, out_dir)
    questions = json.loads(Path(result.sample_questions_path).read_text(encoding="utf-8"))
    answers = [answer_question(result.out_dir, question, top_k=3, generate_steps=16) for question in questions]
    report = {"ok": True, "training": result.as_dict(), "answers": answers}
    Path(result.out_dir, "smoke_test_answers.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


__all__ = [
    "DOCS_AI_FORMAT",
    "DocsChunk",
    "DocsTrainingResult",
    "find_markdown_files",
    "clean_markdown",
    "extract_title",
    "tokenize_for_search",
    "chunk_text",
    "build_docs_dataset",
    "load_docs_dataset",
    "train_docs_model",
    "rank_chunks",
    "answer_question",
    "run_training_smoke_test",
]
