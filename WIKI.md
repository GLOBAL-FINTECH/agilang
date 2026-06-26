# AGILANG Wiki

Welcome to the AGILANG wiki index. This page maps the complete AGILANG learning path from beginner syntax to professional full-stack development, AIFlow, and blockchain.

---

## Start here

Read the full beginner-to-professional manual:

```text
docs/AGILANG_BEGINNER_TO_PROFESSIONAL_WIKI.md
```

Then use the deep reference index:

```text
docs/AGILANG_DOCUMENTATION_INDEX.md
```

---

## Complete documentation set

| Document | Purpose |
|---|---|
| `docs/AGILANG_BEGINNER_TO_PROFESSIONAL_WIKI.md` | Beginner-to-professional AGILANG bootcamp/manual |
| `docs/AGILANG_DOCUMENTATION_INDEX.md` | Documentation map and learning order |
| `docs/AGILANG_SYNTAX_AND_STDLIB_DEEP_REFERENCE.md` | Deep syntax, standard-library patterns, strings, lists, dictionaries, functions, modules and style |
| `docs/AGILANG_AGS_TEMPLATE_DEEP_REFERENCE.md` | `.ags` templates, layouts, escaping, forms, errors, dashboards and template safety |
| `docs/AGILANG_WEB_DATABASE_AUTH_DEEP_REFERENCE.md` | Routes, controllers, APIs, database, auth, sessions, CSRF, middleware and deployment |
| `docs/AGILANG_ERROR_DEBUGGING_DEEP_REFERENCE.md` | 404, 500, 422, 401, 403, 419, 429, logging, debugging and incident response |
| `docs/AGILANG_AI_BLOCKCHAIN_DEEP_REFERENCE.md` | AIFlow, TorchCompat, ONNX, GPU gates, distributed runtime, blockchain, RPC, beacon and validators |
| `docs/AIFLOW_PRODUCTION_UPGRADE.md` | AIFlow production upgrade details and boundaries |

---

## What the wiki teaches

- AGILANG syntax
- variables, constants, functions, conditions and loops
- strings, lists and dictionaries
- structs, enums, imports and modules
- CLI usage
- web app project structure
- routes and controllers
- `.ags` templates
- layouts and pages
- forms and authentication
- sessions and cookies
- database and models
- safe SQL and migrations
- JSON APIs
- middleware and security
- 404 simulation and fixes
- 500 simulation, error collection and fixes
- validation errors
- debugging and testing
- AIFlow usage
- TorchCompat
- ONNX bridge
- GPU backend gates
- distributed runtime
- blockchain development
- RPC and beacon simulation
- deployment checklist
- professional coding standards
- A-to-Z learning path

---

## Recommended order

```text
1. Beginner manual
2. Syntax and standard-library deep reference
3. AGS template deep reference
4. Web/database/auth deep reference
5. Error/debugging deep reference
6. AI/blockchain deep reference
7. AIFlow production upgrade notes
```

---

## Quick validation

```bash
python -m pytest tests/test_aiflow_production_upgrade.py
python -m pytest
```

---

## Daily developer workflow

```bash
agi check src/main.agi
agi typecheck src/main.agi
agi ai doctor
python -m compileall -q agilang tests
python -m pytest
```

For blockchain projects:

```bash
agi chain status --root .
agi chain ethereum-consensus-check
agi beacon status
```
