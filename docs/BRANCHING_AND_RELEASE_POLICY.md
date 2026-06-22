# AGILANG Branching and Release Policy

Repository: `GLOBAL-FINTECH/agilang`

## Purpose

AGILANG separates the language runtime from deployable starter applications and specialized implementation tracks. The `main` branch is reserved for the stable AGILANG runtime and framework core. Full starter applications and specialized blockchain implementation work should live in dedicated branches.

## Branch Roles

| Branch | Purpose | Rules |
|---|---|---|
| `main` | Stable AGILANG runtime branch | Runtime, CLI, parser, AGS engine, compiler/runtime bridge, standard library, stable blockchain/runtime modules, runtime documentation, and tests only. |
| `dev` | Active runtime development branch | Runtime and framework changes are prepared and tested here before promotion to `main`. |
| `blog` | Public web app starter branch | Blog/news/social starter app, `.ags` templates, authentication, password reset, SMTP/email configuration, admin/user UI, and starter documentation. |
| `evm-chain-implementations` | Dedicated EVM chain implementation branch | JSON-RPC, MetaMask-compatible network connection, EVM/SBQ chain experiments, wallet RPC tests, and chain implementation documentation. |

## Main Branch Boundary

The `main` branch must not become the full public web application branch or the experimental EVM implementation branch. It should remain clean and focused on the AGILANG runtime.

This branch is for AGILANG/SBQ EVM chain implementation work. It should contain the JSON-RPC, MetaMask, wallet, local RPC, and EVM execution integration notes needed to develop the EVM-chain layer.

- AGILANG runtime source
- CLI commands such as `agi` and `agilang`
- parser, checker, formatter, AST, execution tools, and runtime bridge
- AGS renderer/runtime support
- standard library modules
- stable blockchain/runtime modules
- runtime tests
- runtime installation documentation
- short links to starter or implementation branches

- Ethereum-style JSON-RPC work
- MetaMask-compatible local network setup
- SBQ/EVM chain configuration
- wallet read APIs
- transaction lookup and receipt APIs
- RPC smoke testing
- EVM execution integration
- production hardening notes

- full blog application as the root app
- full social media app as the root app
- full dating app as the root app
- demo databases
- uploaded media
- production user content
- public-facing app dashboards that are not required by runtime tests
- experimental EVM chain implementation packages as the root branch

```text
evm-chain-implementations → dev → main
```

## Main Branch Boundary

The `main` branch must remain clean and focused on the AGILANG runtime. It should not become the full public web application branch or the experimental EVM chain branch.

## Blog Branch Boundary

## EVM Chain Implementation Boundary

The `evm-chain-implementations` branch is the dedicated branch for AGILANG/SBQ EVM chain implementation work.

It should include:

- JSON-RPC server documentation
- MetaMask network setup documentation
- local RPC smoke tests
- EVM execution integration notes
- SBQ/EVM chain configuration notes
- wallet/app connectivity boundaries
- production hardening checklist

Development in this branch should not automatically redefine `main` as an EVM public network client. Stable, reviewed runtime improvements may be promoted into `dev` and later `main` after validation.

## Development Flow

## Development Commands

```bash
# runtime work
git checkout dev

# web starter work
git checkout blog
git pull origin blog
# make web app starter changes
git add .
git commit -m "starter: describe change"
git push origin blog
```

EVM chain implementation development:

```bash
git checkout evm-chain-implementations
git pull origin evm-chain-implementations
# make EVM/RPC implementation changes
git add .
git commit -m "evm: describe chain implementation change"
git push origin evm-chain-implementations
```

## Public-Facing Branch

If the GitHub landing page should show the web app starter documentation, set the default branch to `blog`:

```text
GitHub → Repository → Settings → Branches → Default branch → blog
```

If the default branch remains `main`, the top of `README.md` must clearly state that `main` is runtime-only and link users to the `blog` branch for the public web app starter.

## Release Tags

# EVM chain work
git checkout evm-chain-implementations
```

EVM implementation releases should be tagged from `evm-chain-implementations`:

```bash
git checkout evm-chain-implementations
git tag evm-chain-v1.9.6
git push origin evm-chain-v1.9.6
```

## Final Rule

`main` is the AGILANG runtime branch.  
`dev` is the active runtime development branch.  
`blog` is the public AGILANG web app starter branch.  
`evm-chain-implementations` is the AGILANG/SBQ EVM chain implementation branch.
