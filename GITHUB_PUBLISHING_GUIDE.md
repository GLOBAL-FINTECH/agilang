# Publish AGILANG on GitHub

## 1. Recommended repository layout

```text
agilang/
├─ agilang/                  # language runtime package
├─ examples/                 # sample AGILANG programs
├─ templates/                # AGS starter templates
├─ docs/                     # language, CLI, hosting, AGS, blockchain docs
├─ tests/                    # runtime/compiler tests
├─ .github/workflows/ci.yml  # automated validation
├─ pyproject.toml
├─ README.md
├─ LICENSE
└─ CHANGELOG.md
```

This uploaded starter currently keeps the runtime in `docs/agilang` and `vendor/agilang`. For a public language repository, promote the runtime package to root-level `agilang/`, then keep app starters in `templates/`.

## 2. Create the GitHub repo

```bash
git init
git add .
git commit -m "Initial AGILANG reactive AGS language release"
git branch -M main
git remote add origin https://github.com/<OWNER>/agilang.git
git push -u origin main
```

## 3. Tag the release

```bash
git tag v2.0.0
git push origin v2.0.0
```

## 4. CI checks to require before release

```bash
python -m agilang --version
python -m agilang check src tests
python -m agilang test
python -m agilang run tests/test_main.agi
```

## 5. Suggested README positioning

AGILANG is a backend-first programming language and runtime for reactive AGS web apps, live APIs, WebRTC signaling, blockchain/devnet tooling, and systems-style Python/C hybrid execution.

## 6. What I still need to publish it for you

To publish directly, provide the GitHub owner/repo target or create an empty repository and confirm the remote URL. Without repository authorization, this package includes the exact guidance and CI files needed for manual publishing.
