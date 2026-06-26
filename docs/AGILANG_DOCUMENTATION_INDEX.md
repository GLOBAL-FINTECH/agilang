# AGILANG Documentation Index

This index organizes the AGILANG documentation into a clear beginner-to-professional learning path.

---

## Start here

| Document | Purpose |
|---|---|
| `WIKI.md` | Root wiki entry point |
| `docs/AGILANG_BEGINNER_TO_PROFESSIONAL_WIKI.md` | Main beginner-to-professional bootcamp/manual |
| `docs/AGILANG_DOCUMENTATION_INDEX.md` | This documentation map |

---

## Deep references

| Document | What it teaches |
|---|---|
| `docs/AGILANG_SYNTAX_AND_STDLIB_DEEP_REFERENCE.md` | Deep syntax, variables, constants, strings, lists, dictionaries, functions, structs, enums, imports, common standard-library patterns and professional style |
| `docs/AGILANG_CLI_AND_DEVELOPER_WORKFLOW_REFERENCE.md` | CLI commands, daily developer workflow, AIFlow commands, blockchain commands, testing, Git workflow and deployment checks |
| `docs/AGILANG_AGS_TEMPLATE_DEEP_REFERENCE.md` | AGS pages, layouts, escaped output, raw trusted HTML, forms, validation messages, error pages, dashboards and template safety |
| `docs/AGILANG_WEB_DATABASE_AUTH_DEEP_REFERENCE.md` | Routes, controllers, APIs, database, safe SQL, models, migrations, authentication, authorization, sessions, CSRF, middleware and deployment checklist |
| `docs/AGILANG_ERROR_DEBUGGING_DEEP_REFERENCE.md` | 404, 500, 422, 401, 403, 419, 429, syntax errors, import errors, template errors, database errors, logging, incident response and tests |
| `docs/AGILANG_AI_BLOCKCHAIN_DEEP_REFERENCE.md` | AIFlow, AGIRecord, image preprocessing, CNNs, tokenizer, language models, TorchCompat, ONNX, GPU gates, distributed runtime, blockchain, RPC, beacon and validators |
| `docs/AGILANG_DOCS_AI_TRAINING_TEST.md` | How to train and test a small local AGILANG docs AI model from README/WIKI/docs Markdown files |
| `docs/AIFLOW_PRODUCTION_UPGRADE.md` | AIFlow production upgrade boundaries, commands and deployment gates |

---

## Recommended learning order

### Phase 1 — Beginner language basics

Read:

```text
docs/AGILANG_BEGINNER_TO_PROFESSIONAL_WIKI.md
docs/AGILANG_SYNTAX_AND_STDLIB_DEEP_REFERENCE.md
```

Practice:

```text
hello.agi
calculator.agi
users-list.agi
safe-divide.agi
```

---

### Phase 2 — CLI and professional workflow

Read:

```text
docs/AGILANG_CLI_AND_DEVELOPER_WORKFLOW_REFERENCE.md
```

Practice:

```bash
agi --help
agi run hello.agi
agi check hello.agi
agi typecheck hello.agi
python -m pytest
```

---

### Phase 3 — Web application development

Read:

```text
docs/AGILANG_AGS_TEMPLATE_DEEP_REFERENCE.md
docs/AGILANG_WEB_DATABASE_AUTH_DEEP_REFERENCE.md
```

Practice:

```text
home page
login page
dashboard page
JSON health API
custom 404 page
custom 500 page
```

---

### Phase 4 — Professional error handling

Read:

```text
docs/AGILANG_ERROR_DEBUGGING_DEEP_REFERENCE.md
```

Practice:

```text
simulate /missing-route -> 404
simulate /simulate-500 -> 500
invalid form -> 422
unauthenticated API -> 401
admin-only page -> 403
```

---

### Phase 5 — AIFlow developer

Read:

```text
docs/AIFLOW_PRODUCTION_UPGRADE.md
docs/AGILANG_AI_BLOCKCHAIN_DEEP_REFERENCE.md
docs/AGILANG_DOCS_AI_TRAINING_TEST.md
```

Practice:

```bash
agi ai capabilities
agi ai doctor
agi ai tokenizer-train --text "agilang builds ai" --out models/tokenizer.json
agi ai lm-train --input corpus.txt --out models/domain-lm.agi-model
agi ai onnx-status
agi ai gpu-status
python tools/train_agilab_docs_ai.py --root . --out storage/agilab-docs-ai --smoke-test
```

---

### Phase 6 — Blockchain developer

Read:

```text
docs/AGILANG_AI_BLOCKCHAIN_DEEP_REFERENCE.md
```

Practice:

```bash
agi new my-chain --template blockchain --chain-id 1900 --symbol SBQ --force
agi chain status --root .
agi chain rpc --root . --host 127.0.0.1 --port 8545
agi beacon simulate --validators 64 --epochs 2
```

---

## Daily professional workflow

```bash
agi check src/main.agi
agi typecheck src/main.agi
python -m compileall -q agilang tests
python -m pytest
agi ai doctor
```

For blockchain projects:

```bash
agi chain status --root .
agi chain ethereum-consensus-check
```

For AGILANG docs AI training:

```bash
python tools/train_agilab_docs_ai.py --root . --out storage/agilab-docs-ai --ask "What is AGILANG?"
python -m pytest tests/test_docs_ai_trainer.py -q
```

---

## Documentation gaps policy

When a runtime feature is still evolving, the documentation must say so clearly. Do not document planned features as complete production capability.

Use these labels:

```text
Implemented
Production-facing
Reference runtime
Optional backend required
Experimental
Planned
Not implemented yet
```

---

## Final path

To become a professional AGILANG developer:

```text
syntax -> modules -> CLI -> web routes -> controllers -> templates -> auth -> database -> APIs -> errors -> tests -> AIFlow -> docs AI training -> blockchain -> deployment
```
