#!/usr/bin/env python
"""Train and test a small AGILANG documentation AI model.

Usage:

    python tools/train_agilab_docs_ai.py --root . --out storage/agilab-docs-ai
    python tools/train_agilab_docs_ai.py --root . --out storage/agilab-docs-ai --ask "What is AGILANG?"

The tool scans Markdown files, builds a JSONL dataset, trains a small AGILANG
language model, and returns retrieval-grounded answers from the docs corpus.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Allow running directly from a source checkout without package installation.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agilang.docs_ai_trainer import answer_question, run_training_smoke_test, train_docs_model


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train a small AGILANG docs AI model from Markdown files")
    parser.add_argument("--root", default=".", help="Repository root to scan for Markdown files")
    parser.add_argument("--out", default="storage/agilab-docs-ai", help="Output directory for dataset/model/report")
    parser.add_argument("--merges", type=int, default=300, help="BPE merges for tokenizer training")
    parser.add_argument("--order", type=int, default=3, help="N-gram order for the small language model")
    parser.add_argument("--max-words", type=int, default=120, help="Maximum words per docs chunk")
    parser.add_argument("--ask", help="Ask a question after training")
    parser.add_argument("--smoke-test", action="store_true", help="Run sample questions after training")
    args = parser.parse_args(argv)

    result = train_docs_model(args.root, args.out, merges=args.merges, order=args.order, max_words=args.max_words)
    print(json.dumps({"event": "trained", **result.as_dict()}, indent=2))

    if args.smoke_test:
        report = run_training_smoke_test(args.root, args.out)
        print(json.dumps({"event": "smoke_test", "answers": report["answers"]}, indent=2))

    if args.ask:
        answer = answer_question(args.out, args.ask)
        print(json.dumps({"event": "answer", **answer}, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
