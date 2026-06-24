# AGILANG Preliminary Security Audit — 2026

Repository: `GLOBAL-FINTECH/agilang`  
Audit type: defensive static review through GitHub connector  
Scope: CLI, translator/runtime execution model, web helpers, security helpers, database helpers, blockchain/beacon boundary documentation, and CI security posture.

## Executive Statement

AGILANG is a real programming language/runtime toolkit with CLI, `.agi` execution, `.ags` templates, web helpers, database helpers, blockchain/private-chain modules, and beacon-style consensus tooling. The current security posture is acceptable for local development, demos, education, private-chain prototyping, and controlled internal testing.

It should not yet be marketed as hardened public-network blockchain infrastructure or as a sandboxed execution environment. The codebase translates `.agi` into Python and then executes it, which means `.agi` files must be treated as trusted source code.

## High-Impact Findings

### 1. Trusted code execution boundary

AGILANG executes translated Python from `.agi` files. This is expected for a programming language/runtime, but it is not a sandbox. Running untrusted `.agi` files can execute host-level code through the Python backend.

**Status:** documented in `SECURITY.md`.  
**Required next patch:** add an explicit `--trusted` or `--allow-unsafe` execution acknowledgement for downloaded/untrusted files, or add a future restricted interpreter mode.

### 2. Public web deployment boundary

The built-in web server is suitable for development and controlled internal deployments. Public internet deployment requires reverse proxy hardening, TLS, body limits, rate limiting, auth, and observability.

**Status:** documented in `SECURITY.md`.  
**Required next patch:** add generated app security middleware by default for web/API templates.

### 3. Database identifier injection risk in generated migrations

Database value queries use parameters in some areas, but table/column names are interpolated into SQL for migration generation and database operations. Identifiers need strict validation/quoting helpers.

**Status:** identified.  
**Required next patch:** add identifier validation helpers and apply them to database/table commands.

### 4. Static file and template boundaries

Static-file serving resolves paths and blocks directory traversal. Template rendering escapes normal `{{ value }}` output and allows trusted raw `{{{ value }}}` output. Raw output must be treated as trusted-only.

**Status:** acceptable with documented caution.  
**Required next patch:** document raw template output and add tests proving traversal is blocked.

### 5. Blockchain and beacon-chain production boundary

The blockchain/beacon modules are suitable for devnet/private-chain simulation and framework extension. Public networks or real-value systems require independent audits, validator key management, authenticated RPC, peer scoring, slashing enforcement, state persistence review, fork-choice review, DoS controls, and stress testing.

**Status:** documented in `SECURITY.md`.

## Security Patches Added in This Branch

- Added `SECURITY.md` with vulnerability reporting, secure deployment boundaries, and blockchain/runtime warnings.
- Added GitHub Actions security workflow:
  - `pytest`
  - `bandit`
  - `pip-audit`
- Added Dependabot configuration for Python dependencies and GitHub Actions.
- Added security tooling to `pyproject.toml` development extras.

## Recommended Next Code Patches

1. Add SQL identifier validation helpers and patch database commands.
2. Add CLI warning when running `.agi` files outside the current project root.
3. Add tests for static-file traversal prevention.
4. Add tests for signed-cookie tamper and expiry behavior.
5. Add default web/API scaffold middleware: security headers, body limit, and rate limiting.
6. Add explicit docs that `{{{ raw }}}` is trusted-only HTML.
7. Add release checklist requiring `pytest`, `bandit`, and `pip-audit` pass.

## Current Production Security Classification

| Area | Classification |
| --- | --- |
| Local CLI/runtime | Development-ready, trusted-code only |
| Web framework | Development/internal-service ready |
| Generated web apps | Needs default middleware hardening |
| Database helpers | Needs identifier validation patch |
| Blockchain modules | Devnet/private-chain prototype |
| Public real-value blockchain | Not ready without further audit/hardening |

## Final Statement

This audit branch improves the security process and documents the most important boundaries. The most important code-level follow-up is database identifier hardening and generated-app secure defaults.
