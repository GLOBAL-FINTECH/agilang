#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agilang.docs_ai_answer_composer import ask_docs_ai, save_answer


def print_pretty(answer: dict) -> None:
    print(f"Question: {answer['question']}\n")
    print(f"Intent: {answer['intent']}\n")
    print(f"Answer: {answer['answer']}\n")
    if answer.get("code"):
        print("Code:")
        print(answer["code"])
        print("")
    print(f"Confidence: {answer['confidence']:.2f}\n")
    print("Sources:")
    for source in answer.get("sources", []):
        print(f"  - {source['title']} (score: {source['score']:.2f})")
        print(f"    {source['source']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask the AGILANG docs AI composer a question")
    parser.add_argument("--model-dir", default="storage/agilab-docs-ai")
    parser.add_argument("--question", required=True)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--out", help="Optional JSON output path")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    answer = ask_docs_ai(args.model_dir, args.question, top_k=args.top_k)
    if args.out:
        save_answer(args.out, answer)
    if args.pretty:
        print_pretty(answer)
    else:
        print(json.dumps(answer, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
