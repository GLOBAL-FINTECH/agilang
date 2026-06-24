# AGILANG Security Battle-Test Report — 2026

## Scope

This defensive test pass covered the AGILANG Python runtime, web framework, CGI runtime, CLI database helpers, ZK helper exports, native runtime version alignment, and regression tests.

## Commands run

```bash
python -m pytest -q
python -m pytest tests/test_security_runtime.py -q
python -m compileall -q agilang
python -m bandit -r agilang -c pyproject.toml -q
```

## Results

| Check | Result |
|---|---:|
| Full pytest suite | 107 passed |
| Security regression tests | 7 passed |
| Python bytecode compile | Passed |
| Bandit | Not executed in sandbox: module not installed |

## Patches prepared

1. Restored the public `zk_verify_commit` API alias so package import does not fail.
2. Hardened static file handling against percent-encoded parent traversal.
3. Hardened CGI request-path normalization with URL decoding before routing.
4. Added safe SQL identifier validation and quoting for ORM table/column interpolation.
5. Added safe SQL identifier validation and quoting for CLI MySQL database/table migration helpers.
6. Added stricter generated migration column-definition validation.
7. Aligned hybrid/native runtime version strings with package version `2.1.0`.
8. Updated scaffold tests to match `.ags` resource paths.
9. Stabilized WebRTC signaling test to ignore join-notification ordering and assert actual offer delivery.
10. Added regression tests for encoded static path traversal and unsafe ORM identifiers.

## Remaining production limits

AGILANG still executes trusted `.agi` source by translating it to Python. This is correct for a programming language runtime, but it is not a sandbox. Run only trusted `.agi` source on production systems.

The built-in HTTP/WebSocket servers remain development/internal-service components. Internet-facing production deployment should still use a hardened reverse proxy, TLS, request-size limits, rate limits, centralized logging, and process isolation.

The blockchain modules remain suitable for devnet/private-chain experiments and controlled test networks. Public real-value networks require deeper cryptographic validator signing, state trie/storage design, peer scoring, slashing economics, DoS controls, fork-choice review, stress testing, and independent security audits.
