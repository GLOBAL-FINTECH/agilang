# AGILANG Docs AI Training Test

This guide shows how to test AGILANG AI training using the repository Markdown documentation as the training corpus.

The goal is to prove the full local flow:

```text
Markdown docs -> JSONL dataset -> text corpus -> tokenizer -> small language model -> retrieval-grounded answer test
```

---

## 1. What this test does

The training tool scans all `.md` files in the AGILANG repository, including:

```text
README.md
WIKI.md
docs/*.md
```

Then it creates:

```text
storage/agilab-docs-ai/agilang_docs_dataset.jsonl
storage/agilab-docs-ai/agilang_docs_corpus.txt
storage/agilab-docs-ai/agilang_docs_lm.agi-model
storage/agilab-docs-ai/agilang_docs_dataset_summary.json
storage/agilab-docs-ai/training_summary.json
storage/agilab-docs-ai/sample_questions.json
storage/agilab-docs-ai/smoke_test_answers.json
```

---

## 2. Run the training test on Windows

From the AGILANG repository root:

```powershell
python tools/train_agilab_docs_ai.py --root . --out storage/agilab-docs-ai --smoke-test
```

Ask a direct question after training:

```powershell
python tools/train_agilab_docs_ai.py --root . --out storage/agilab-docs-ai --ask "What is AGILANG?"
```

Ask about web apps:

```powershell
python tools/train_agilab_docs_ai.py --root . --out storage/agilab-docs-ai --ask "How do I create an AGILANG web app?"
```

Ask about AIFlow:

```powershell
python tools/train_agilab_docs_ai.py --root . --out storage/agilab-docs-ai --ask "What is AIFlow?"
```

Ask about blockchain:

```powershell
python tools/train_agilab_docs_ai.py --root . --out storage/agilab-docs-ai --ask "How do I create a blockchain project in AGILANG?"
```

---

## 3. Run focused tests

```powershell
python -m pytest tests/test_docs_ai_trainer.py -q
```

Full AIFlow-related validation:

```powershell
python -m pytest tests/test_docs_ai_trainer.py tests/test_aiflow_production_upgrade.py -q
```

---

## 4. What a successful output means

A successful training event looks like this:

```json
{
  "event": "trained",
  "ok": true,
  "markdown_files": 10,
  "chunks": 100,
  "dataset_path": ".../agilang_docs_dataset.jsonl",
  "model_path": ".../agilang_docs_lm.agi-model"
}
```

The answer output includes:

```json
{
  "event": "answer",
  "ok": true,
  "answer_mode": "retrieval_plus_small_lm",
  "grounded_context": [],
  "small_model_generated_text": "..."
}
```

---

## 5. How to judge intelligence honestly

This is a small local model, not a large GPT-style instruction model.

Judge it in two parts:

### A. Retrieval quality

Check whether `grounded_context` finds the correct AGILANG docs.

For the question:

```text
What is AIFlow?
```

Good context should mention:

```text
AIFlow
AGIRecord
image preprocessing
CNN training
BPE tokenizer
language model
TorchCompat
ONNX
GPU gate
distributed runtime
```

### B. Small model generation

Check whether `small_model_generated_text` uses AGILANG-related vocabulary.

The generated text may be repetitive because the local model is a small n-gram model. That is expected.

---

## 6. Why retrieval is included

A small n-gram language model alone cannot reason like a large AI assistant. It learns local word patterns from the docs.

The retrieval layer makes the test useful by grounding answers in the Markdown documentation.

This is the correct honest architecture for a small local documentation assistant:

```text
question -> retrieve relevant docs chunks -> small model continuation -> grounded answer package
```

---

## 7. Files added for this feature

```text
agilang/docs_ai_trainer.py
tools/train_agilab_docs_ai.py
tests/test_docs_ai_trainer.py
docs/AGILANG_DOCS_AI_TRAINING_TEST.md
```

---

## 8. Recommended next improvement

After this passes, the next step is to add an AGILANG CLI wrapper:

```bash
agi ai docs-train --root . --out storage/agilab-docs-ai
agi ai docs-ask --model-dir storage/agilab-docs-ai --question "What is AGILANG?"
```

This guide uses the Python tool first because it is easier to test directly and does not disturb the existing CLI command parser.

---

## Final status

This test proves whether AGILANG can train a small local AI model using its own documentation corpus and return grounded answers about AGILANG, AGS, AIFlow, and blockchain.
