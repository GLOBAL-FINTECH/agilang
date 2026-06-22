# AGILANG Branching and Release Policy

Repository: `GLOBAL-FINTECH/agilang`

## Purpose

AGILANG separates the stable runtime, public starter applications, and specialized implementation tracks. The `main` branch is reserved for the AGILANG runtime and framework core. Full starter applications and EVM chain implementation work live in dedicated branches.

## Branch Roles

| Branch | Purpose | Rules |
|---|---|---|
| `main` | Stable AGILANG runtime branch | Runtime, CLI, parser, AGS engine, compiler/runtime bridge, standard library, stable blockchain/runtime modules, runtime documentation, and tests only. |
| `dev` | Active runtime development branch | Runtime and framework changes are prepared and tested here before promotion to `main`. |
| `blog` | Public web app starter branch | Blog/news/social starter app, `.ags` templates, authentication, password reset, SMTP/email configuration, admin/user UI, and starter documentation. |
| `evm-chain-implementations` | Dedicated EVM chain implementation branch | JSON-RPC, MetaMask-compatible local-network work, SBQ/EVM implementation experiments, wallet RPC tests, and EVM chain documentation. |

## EVM Chain Branch Boundary

This branch is for AGILANG/SBQ EVM chain implementation work. It should contain the JSON-RPC, MetaMask, wallet, local RPC, and EVM execution integration notes needed to develop the EVM-chain layer.

Use this branch for:

- Ethereum-style JSON-RPC work
- MetaMask-compatible local network setup
- SBQ/EVM chain configuration
- wallet read APIs
- transaction lookup and receipt APIs
- RPC smoke testing
- EVM execution integration
- production hardening notes

Stable improvements can be promoted through:

```text
evm-chain-implementations → dev → main
```

## Main Branch Boundary

The `main` branch must remain clean and focused on the AGILANG runtime. It should not become the full public web application branch or the experimental EVM chain branch.

## Blog Branch Boundary

The `blog` branch is the public AGILANG web app starter branch. It should contain the complete starter-kit experience for developers who want to build web applications using AGILANG and `.ags` views.

## Development Commands

```bash
# runtime work
git checkout dev

# web starter work
git checkout blog

# EVM chain work
git checkout evm-chain-implementations
```

## Final Rule

`main` is the AGILANG runtime branch.  
`dev` is the active runtime development branch.  
`blog` is the public AGILANG web app starter branch.  
`evm-chain-implementations` is the AGILANG/SBQ EVM chain implementation branch.
