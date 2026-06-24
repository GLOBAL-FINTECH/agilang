# Security Policy

AGILANG is a programming language/runtime and blockchain development toolkit. Security reports should be handled carefully because runtime, compiler, web, database, and blockchain code can affect generated applications.

## Supported Versions

| Version | Security support |
| --- | --- |
| 2.x | Supported for security fixes |
| < 2.0 | Best-effort only |

## Reporting a Vulnerability

Please do **not** disclose suspected vulnerabilities publicly until they are assessed and fixed.

Report security issues by opening a private advisory on GitHub or by contacting the project maintainer directly.

Include:

- Affected version or commit SHA
- Affected module or command
- Minimal reproduction steps
- Expected impact
- Whether the issue affects local-only tooling, generated apps, or network-exposed services

## Security Boundaries

AGILANG executes trusted `.agi` source code by translating it to Python. It is **not a sandbox**. Do not run untrusted `.agi` files on production machines or developer machines with sensitive credentials.

The built-in web server is intended for development, local tools, demos, and controlled internal services. Internet-facing production deployments should use a reverse proxy, TLS, logging, rate limiting, request-size limits, and deployment-specific hardening.

The blockchain and beacon-chain modules are suitable for development, education, private-chain prototyping, and controlled test networks. Public-network or real-value deployment requires independent security audits, adversarial testing, validator key management, peer scoring, slashing enforcement, state persistence review, networking hardening, and stress testing.

## Secure Defaults Checklist

Before deploying AGILANG-generated apps:

- Use HTTPS/TLS at the edge.
- Keep debug mode disabled.
- Set secure, HTTP-only cookies.
- Add request body limits.
- Add rate limits to public endpoints.
- Store secrets outside source control.
- Run `pytest`, `bandit`, and `pip-audit` during CI.
- Review `.agi` files before execution.
- Do not expose private beacon, validator, or RPC APIs without authentication and network controls.
