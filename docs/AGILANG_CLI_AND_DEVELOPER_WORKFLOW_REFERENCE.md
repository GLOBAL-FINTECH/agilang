# AGILANG CLI and Developer Workflow Reference

This guide teaches the daily commands and workflows used by AGILANG developers.

Use this document together with:

```text
docs/AGILANG_BEGINNER_TO_PROFESSIONAL_WIKI.md
docs/AGILANG_DOCUMENTATION_INDEX.md
```

---

## 1. Basic CLI commands

Show help:

```bash
agi --help
agilang --help
```

Run a file:

```bash
agi run hello.agi
```

Check syntax:

```bash
agi check src/main.agi
```

Typecheck:

```bash
agi typecheck src/main.agi
```

Show tokens:

```bash
agi tokens src/main.agi
```

Show AST:

```bash
agi ast src/main.agi
```

Format:

```bash
agi fmt src/main.agi
```

Run tests:

```bash
agi test
python -m pytest
```

Open REPL:

```bash
agi repl
```

Doctor check:

```bash
agi doctor
```

---

## 2. Beginner workflow

When learning AGILANG:

```bash
agi run hello.agi
agi check hello.agi
agi typecheck hello.agi
```

Recommended practice files:

```text
hello.agi
calculator.agi
users.agi
safe_divide.agi
```

---

## 3. Web developer workflow

Create or work inside an app:

```bash
cd my-app
```

Run checks:

```bash
agi check src/main.agi
agi typecheck src/main.agi
python -m pytest
```

Common files to edit:

```text
routes/web.agi
routes/api.agi
app/controllers/*.agi
resources/views/*.ags
config/*.json
```

Debug route problems:

```text
[ ] route is registered
[ ] route file is imported
[ ] controller function exists
[ ] HTTP method matches form/API request
[ ] template file exists
```

---

## 4. AIFlow workflow

Check AI capabilities:

```bash
agi ai capabilities
agi ai doctor
```

Tokenizer:

```bash
agi ai tokenizer-train --text "agilang builds ai" --out models/tokenizer.json
agi ai tokenizer-encode --model models/tokenizer.json --text "agilang builds ai"
agi ai tokenizer-decode --model models/tokenizer.json --ids "[2,4,5,3]"
```

Language model:

```bash
agi ai lm-train --input corpus.txt --out models/domain-lm.agi-model --order 3
agi ai lm-generate --model models/domain-lm.agi-model --prompt "agilang" --steps 32
```

ONNX/GPU/distributed status:

```bash
agi ai onnx-status
agi ai gpu-status
agi ai distributed-status
```

Image preprocessing:

```bash
agi ai preprocess-image --input document.png --out storage/document.json --rows 224 --cols 224 --mode L
```

Run AIFlow tests:

```bash
python -m pytest tests/test_aiflow_production_upgrade.py
```

---

## 5. Blockchain workflow

Create a chain:

```bash
agi new my-chain --template blockchain --chain-id 1900 --symbol SBQ --force
cd my-chain
```

Check status:

```bash
agi chain status --root .
```

Start RPC:

```bash
agi chain rpc --root . --host 127.0.0.1 --port 8545
```

Beacon:

```bash
agi beacon status
agi beacon simulate --validators 64 --epochs 2
```

Ethereum consensus profile:

```bash
agi chain ethereum-consensus-capabilities
agi chain ethereum-consensus-write-config --chain-id 901900
agi chain ethereum-consensus-check
agi chain ethereum-consensus-sim --slots 8
agi chain consensus-replacement-plan --network private-fork --consensus ethereum-pos-replica
```

---

## 6. Full validation before commit

Run:

```bash
agi check src/main.agi
agi typecheck src/main.agi
python -m compileall -q agilang tests
python -m pytest
```

If working on AI:

```bash
agi ai doctor
python -m pytest tests/test_aiflow_production_upgrade.py
```

If working on blockchain:

```bash
agi chain status --root .
agi chain ethereum-consensus-check
```

---

## 7. Git workflow

Recommended professional workflow:

```bash
git status
git checkout -b feature/my-change
# edit files
python -m pytest
git add .
git commit -m "Describe the change"
git push origin feature/my-change
```

For direct main updates, be extra careful:

```bash
python -m pytest
python -m compileall -q agilang tests
```

---

## 8. Error workflow

When something breaks:

```text
1. Read the error message
2. Identify file and line
3. Re-run with smallest reproduction
4. Check syntax
5. Check imports
6. Check routes/templates
7. Check config/database
8. Add or update a test
9. Fix the code
10. Run full tests
```

---

## 9. Production deployment workflow

Before production:

```bash
python -m pytest
python -m compileall -q agilang tests
agi ai doctor
```

Checklist:

```text
[ ] debug disabled
[ ] secure environment variables set
[ ] storage writable
[ ] database backed up
[ ] logs private
[ ] routes protected
[ ] admin protected
[ ] API tokens protected
[ ] error pages exist
[ ] CI passing
```

---

## 10. Professional daily habit

Every day:

```text
write small code
check syntax
run tests
update docs
commit clearly
avoid false production claims
```

A professional AGILANG developer should know the CLI as well as the syntax.
