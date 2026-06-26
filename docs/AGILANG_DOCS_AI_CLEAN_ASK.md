# AGILANG Docs AI Clean Ask

This guide explains the clean `docs_ai_ask` command.

The earlier docs AI output could copy raw documentation chunks into the final answer. The clean answer composer fixes that by separating:

```text
clean answer
isolated code/command block
ranked documentation sources
confidence score
```

---

## 1. Train the docs model

```powershell
python tools/train_agilab_docs_ai.py --root . --out storage/agilab-docs-ai --smoke-test
```

---

## 2. Ask a clean question

```powershell
python tools/docs_ai_ask.py --model-dir storage/agilab-docs-ai --question "How do I create a blockchain project in AGILANG?" --pretty
```

Expected answer style:

```text
Question: How do I create a blockchain project in AGILANG?

Intent: blockchain_project

Answer: Use the blockchain scaffold template. Create a new project with a unique chain ID and symbol, then run the chain status, RPC, and beacon simulation commands. The generated project includes chain configuration, genesis configuration, RPC files, validator configuration, source files, and storage.

Code:
agi new my-chain --template blockchain --chain-id 1900 --symbol SBQ --force
cd my-chain
agi chain status --root .
agi chain rpc --root . --host 127.0.0.1 --port 8545
agi beacon simulate --validators 64 --epochs 2
```

---

## 3. Ask other questions

```powershell
python tools/docs_ai_ask.py --model-dir storage/agilab-docs-ai --question "What is AGILANG?" --pretty
python tools/docs_ai_ask.py --model-dir storage/agilab-docs-ai --question "What is AIFlow?" --pretty
python tools/docs_ai_ask.py --model-dir storage/agilab-docs-ai --question "How do I handle 404 and 500 errors?" --pretty
python tools/docs_ai_ask.py --model-dir storage/agilab-docs-ai --question "How do I create JSON API responses in AGILANG?" --pretty
python tools/docs_ai_ask.py --model-dir storage/agilab-docs-ai --question "How do I train the AGILANG docs AI model?" --pretty
```

---

## 4. Save JSON output

```powershell
python tools/docs_ai_ask.py --model-dir storage/agilab-docs-ai --question "What is AGILANG?" --out storage/agilab-docs-ai/answers/what-is-agilang.json
```

---

## 5. Run tests

```powershell
python -m pytest tests/test_docs_ai_answer_composer.py -q
```

Run all docs AI tests:

```powershell
python -m pytest tests/test_docs_ai_trainer.py tests/test_docs_ai_qa_demo.py tests/test_docs_ai_answer_composer.py -q
```

---

## 6. What changed

The clean composer now:

```text
[ ] detects the question intent
[ ] prioritizes primary AGILANG docs over demo/self-test docs
[ ] avoids copying raw chunks as the final answer
[ ] returns a clean answer paragraph
[ ] returns only the useful code/command block in the code field
[ ] still shows sources for verification
```

---

## 7. Honest limitation

This is still a small local docs AI system. It is not GPT-level reasoning. The clean composer improves usefulness by using intent rules and grounded sources from the AGILANG documentation.
