# AGILANG Docs AI Q&A and Code Task Demo

This guide shows how to inspect the AGILANG documentation-trained model by asking real questions and code-writing tasks.

The demo generates two files:

```text
storage/agilab-docs-ai/demo/agilang_docs_ai_qa_demo.json
storage/agilab-docs-ai/demo/agilang_docs_ai_qa_demo.md
```

The Markdown report is the easiest file to read.

---

## 1. Train the documentation model first

From the repository root:

```powershell
python tools/train_agilab_docs_ai.py --root . --out storage/agilab-docs-ai --smoke-test
```

This creates:

```text
storage/agilab-docs-ai/agilang_docs_dataset.jsonl
storage/agilab-docs-ai/agilang_docs_corpus.txt
storage/agilab-docs-ai/agilang_docs_lm.agi-model
storage/agilab-docs-ai/sample_questions.json
storage/agilab-docs-ai/smoke_test_answers.json
```

---

## 2. Run the Q&A and code-task demo

```powershell
python tools/docs_ai_qa_demo.py --model-dir storage/agilab-docs-ai --out storage/agilab-docs-ai/demo
```

Open the Markdown report:

```powershell
notepad storage/agilab-docs-ai/demo/agilang_docs_ai_qa_demo.md
```

Or inspect the JSON:

```powershell
notepad storage/agilab-docs-ai/demo/agilang_docs_ai_qa_demo.json
```

---

## 3. What questions are asked

The demo asks questions like:

```text
What is AGILANG?
How do I install AGILANG and verify the CLI works?
How do I write my first hello world AGI program?
What is the recommended AGILANG full-stack project structure?
How do routes and controllers work in AGILANG web apps?
What are AGS templates used for?
How should AGILANG handle 404 and 500 errors?
How do I create JSON API responses in AGILANG?
What is AIFlow in AGILANG?
What is TorchCompat?
How do I train a small language model using AGILANG docs?
How do I create a blockchain project in AGILANG?
```

---

## 4. What code tasks are asked

The demo asks code-writing tasks like:

```text
Write a hello world AGILANG program.
Write AGILANG routes for home, login, dashboard, and API health.
Write an AGS layout and home page with data rendering.
Write a protected dashboard controller.
Write a JSON API health endpoint.
Write a custom 404 handler and template.
Write a safe 500 error wrapper.
Write commands to train the AGILANG docs AI model.
Write commands to create an AGILANG blockchain project.
```

---

## 5. How to read the report

Each Q&A result includes:

```text
question
grounded documentation context
small model generated text
```

Each code task includes:

```text
task
question asked to the model
grounded documentation context
small model generated text
reference solution
validation hint
```

Important:

```text
The grounded documentation context is the most reliable part.
The small model generated text is a local-model intelligence/vocabulary test.
The reference solution is the expected documentation-grounded code answer.
```

---

## 6. Run tests

```powershell
python -m pytest tests/test_docs_ai_qa_demo.py -q
```

Run all docs-AI tests:

```powershell
python -m pytest tests/test_docs_ai_trainer.py tests/test_docs_ai_qa_demo.py -q
```

---

## 7. Expected successful result

```text
2 passed
```

or for all docs-AI tests:

```text
5 passed
```

---

## 8. Honest model expectation

This is not a large instruction model. It is a small AGILANG-trained documentation model with retrieval grounding.

A good result means:

```text
[ ] It retrieves the correct docs chunks
[ ] It generates AGILANG-related vocabulary
[ ] It produces a readable report
[ ] It includes reference code solutions
[ ] The tests pass
```

---

## 9. Next improvement

The next step is to expose this through AGILANG CLI commands:

```bash
agi ai docs-train --root . --out storage/agilab-docs-ai
agi ai docs-ask --model-dir storage/agilab-docs-ai --question "What is AGILANG?"
agi ai docs-demo --model-dir storage/agilab-docs-ai --out storage/agilab-docs-ai/demo
```

For now, use:

```bash
python tools/train_agilab_docs_ai.py --root . --out storage/agilab-docs-ai --smoke-test
python tools/docs_ai_qa_demo.py --model-dir storage/agilab-docs-ai --out storage/agilab-docs-ai/demo
```
