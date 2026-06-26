#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agilang.docs_ai_qa_demo import run_qa_demo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AGILANG docs AI Q&A demo")
    parser.add_argument("--model-dir", default="storage/agilab-docs-ai")
    parser.add_argument("--out", default="storage/agilab-docs-ai/demo")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--steps", type=int, default=32)
    args = parser.parse_args(argv)

    result = run_qa_demo(args.model_dir, args.out, top_k=args.top_k, generate_steps=args.steps)
    print(json.dumps(result["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
