# AGILANG Applications and Starter Kits

AGILANG is designed to generate useful projects quickly while still allowing developers to edit normal source files.

## Supported application categories

| Category | Purpose |
|---|---|
| Basic app | Learn `.agi`, routes, templates, and CLI basics |
| Web app | Public pages, dashboards, APIs, forms, database-backed pages |
| CMS/blog app | Posts, pages, categories, media, admin publishing workflow |
| Business app | Internal dashboards, operations tools, customer portals |
| Realtime app | Live status pages, notification panels, polling/live data bindings |
| Blockchain app | SBQ chain starter, Beacon layer, validators, staking, RPC, MetaMask local/staging setup |
| EVM/dApp app | EVM RPC integration, wallet-aware frontend, contract tooling track |

## Normal web app starter

```bash
agi new my-web-app
cd my-web-app
agi serve src/main.agi --host 127.0.0.1 --port 8000
```

Expected structure:

```text
my-web-app/
├─ src/main.agi
├─ resources/views/
├─ resources/assets/
├─ database/migrations/
├─ storage/
└─ tests/
```

## CMS/blog starter branch

The `blog` branch is the public web app starter branch. It should showcase AGILANG as a language and framework by including:

- public home page
- blog/news listing
- post detail page
- categories/tags
- admin dashboard
- content editor workflow
- authentication
- password reset
- SMTP/email setup
- `.ags` templates
- database migrations
- deployment guide

Use:

```bash
git clone https://github.com/GLOBAL-FINTECH/agilang.git
cd agilang
git checkout blog
```

## Blockchain starter

```bash
agi new my-chain --template blockchain
```

The blockchain starter generates a complete configurable chain project, not only a sample script.

It includes:

- chain runtime entrypoints
- chain config
- genesis config
- validator config
- staking config
- RPC config
- Beacon config
- Ethereum external-client config
- wallet example config
- MetaMask setup guide
- runbook documentation

## Design rule

A starter kit must never be only a static template. Every visible section should connect to one of the following:

1. a real backend route,
2. a real database table,
3. a real config file,
4. a real runtime module,
5. or a clear empty state when no data exists.

## Recommended starter quality checklist

- clean README
- `.env.example`
- no committed secrets
- database migrations
- seed/demo data separated from production data
- real empty states
- user/admin navigation separation
- tests for generated project files
- docs for all generated commands
- production boundary notes
