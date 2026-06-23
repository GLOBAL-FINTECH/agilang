# AGILANG Programming Language CMS / Blockchain / Blog Starter Kit

> **Main runtime branch:** this branch contains the AGILANG programming language runtime, CLI, parser/runtime tooling, AGS template engine, app scaffolding, blockchain generator, SBQ Beacon layer, EVM/RPC tooling, Ethereum external-client orchestration, and runtime tests. The `blog` branch is the public web/CMS starter branch.

**AGILANG** is a modular programming language and application runtime for building web apps, APIs, dashboards, CMS/blog systems, business apps, real-time apps, and blockchain-enabled applications from one developer-friendly command line.

The goal is simple:

```text
learn the language -> create an app -> run it locally -> scaffold production-ready modules -> deploy
```

AGILANG is designed around `.agi` backend/source files and `.ags` reactive view templates. It also includes optional blockchain tooling so developers can generate a configurable SBQ/EVM-style blockchain project without manually assembling the database, node, validator, consensus, RPC, and wallet configuration from scratch.

**License:** MIT  
**Developed by:** Izukanji Sirwimba, AGILab, Izurex Enterprise Limited

---

## What AGILANG is

AGILANG is both:

1. **A programming language** — syntax, functions, types, structs, enums, imports, and executable `.agi` source files.
2. **An application runtime** — CLI tools, web server helpers, AGS templates, scaffolds, database helpers, testing helpers, and blockchain/runtime modules.

It is not limited to blockchain. Blockchain is one optional application domain inside the runtime.

---

## Recommended starter structure

```text
cms-starter/
├─ agilang.toml
├─ .env.example
├─ src/
│  ├─ main.agi
│  ├─ config.agi
│  ├─ routes/
│  │  ├─ web.agi
│  │  └─ api.agi
│  ├─ controllers/
│  ├─ services/
│  └─ middleware/
├─ resources/
│  ├─ views/
│  │  ├─ layout.ags
│  │  ├─ home.ags
│  │  ├─ blog.ags
│  │  ├─ post.ags
│  │  ├─ admin-dashboard.ags
│  │  ├─ login.ags
│  │  ├─ forgot-password.ags
│  │  └─ reset-password.ags
│  └─ assets/
├─ database/migrations/
├─ storage/
├─ public_html/
└─ tests/
```

---

## Environment and SMTP setup

Create `.env` from `.env.example`:

```env
APP_NAME="AGILANG CMS Starter"
APP_ENV=local
APP_DEBUG=true
APP_URL=http://127.0.0.1:8000
APP_SECRET=change-this-secret

DATABASE_PATH=storage/app.sqlite

MAIL_MAILER=smtp
MAIL_HOST=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-smtp-password
MAIL_ENCRYPTION=tls
MAIL_FROM_ADDRESS=no-reply@example.com
MAIL_FROM_NAME="AGILANG CMS"

PASSWORD_RESET_TOKEN_MINUTES=60
```

Never commit real `.env` credentials.

---

## Password reset workflow

The starter should support:

```text
GET  /forgot-password
POST /forgot-password
GET  /reset-password
POST /reset-password
```

Safe password reset behavior:

1. User enters email.
2. App creates secure token.
3. App stores hashed token.
4. App emails reset link through SMTP.
5. User sets new password.
6. App validates token, expiry, and password confirmation.
7. App updates password hash and marks token used.

Full guide:

```text
docs/CMS_BLOG_STARTER_GUIDE.md
```

---

## AGS example

```ags
@page title="Blog" seo_description="AGILANG CMS blog page."
@layout "layout.ags"
@fetch posts from "/api/posts"

<section class="blog-grid">
  <h1>{{ title }}</h1>
  <div data-repeat="posts">
    <article>
      <h2>{{ item.title }}</h2>
      <p>{{ item.excerpt }}</p>
      <a href="/blog/{{ item.slug }}">Read more</a>
    </article>
  </div>
</section>
```

Backend API:

```agi
fn api_posts(request):
    let posts = db().query("select title, slug, excerpt from posts where status = ? order by published_at desc", ["published"])
    return json_response({"posts": posts})
```

---

## Documentation

| Document | Purpose |
|---|---|
| `docs/WEB_APP_STARTER_GUIDE.md` | Web app starter instructions |
| `docs/CMS_BLOG_STARTER_GUIDE.md` | CMS/blog app structure, routes, password reset, SMTP |
| `docs/AGILANG_WEB_SHOWCASE.md` | How this branch showcases the language |
| `docs/BRANCHING_AND_RELEASE_POLICY.md` | Branch separation policy |

---

## Branch relationship

| Branch | Purpose |
|---|---|
| `main` | AGILANG runtime, language docs, CLI, blockchain runtime |
| `blog` | CMS/blog/web starter kit and public application showcase |
| `dev` | Active framework/runtime development |
## What you can build

| Area | Examples |
|---|---|
| Web apps | landing pages, dashboards, SaaS portals, admin panels |
| CMS/blog apps | posts, categories, pages, media, admin publishing workflow |
| APIs | REST-style JSON APIs, internal services, integrations |
| Realtime apps | live dashboards, polling/live AGS bindings, notifications |
| Business systems | payments, merchant portals, internal operations tools |
| Blockchain apps | SBQ chain starter, validators, staking, JSON-RPC, MetaMask local/staging setup |
| Smart-contract tooling track | EVM chain experiments, contract/dApp workflow, RPC integration |

---

## Install locally

```bash
git clone https://github.com/GLOBAL-FINTECH/agilang.git
cd agilang
python -m pip install -e .
agi --version
```

Expected:

```text
AGILANG 2.1.0
```

---

## Your first AGILANG program

Create `hello.agi`:

```agi
fn main() -> i32:
    let name = "AGILANG"
    print("Hello from " + name)
    return 0
```

Run it:

```bash
agi run hello.agi
```

---

## Basic language syntax

### Variables

```agi
let app_name = "My App"
let count: i32 = 10
const VERSION = "1.0.0"
```

### Functions

```agi
fn greet(name: string) -> string:
    return "Hello, " + name
```

### Conditionals

```agi
if role == "admin":
    print("Admin user")
elif role == "editor":
    print("Editor user")
else:
    print("Normal user")
```

### Structs

```agi
struct User:
    id: i32
    name: string
    email: string
```

### Imports

```agi
import "routes/web.agi"
import "services/mail.agi"
```

For the full beginner guide, read:

```text
docs/LANGUAGE_GUIDE.md
```

---

## Create a web app

```bash
agi new my-web-app
cd my-web-app
agi serve src/main.agi --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

Recommended web app structure:

```text
my-web-app/
├─ agilang.toml
├─ .env.example
├─ src/
│  ├─ main.agi
│  ├─ routes/
│  ├─ controllers/
│  ├─ services/
│  └─ middleware/
├─ resources/
│  ├─ views/*.ags
│  └─ assets/
├─ database/migrations/
├─ storage/
└─ tests/
```

---

## AGS reactive templates

AGILANG views use `.ags` templates:

```ags
@page title="Dashboard" seo_description="AGILANG dashboard example."
@layout "layout.ags"
@fetch stats from "/api/stats"
@live stats from "/api/stats" every 5000

<section class="dashboard">
  <h1>{{ title }}</h1>
  <p>Total users: {{ stats.users }}</p>
  <p>Status: {{ stats.status }}</p>
</section>
```

Backend route example:

```agi
fn api_stats(request):
    return json_response({"users": 100, "status": "online"})
```

---

## Command line basics

Common commands:

```bash
agi --version
agi run src/main.agi
agi serve src/main.agi --host 127.0.0.1 --port 8000
agi check src tests
agi test
agi new my-web-app
agi new my-chain --template blockchain
```

Full CLI documentation:

```text
docs/CLI_REFERENCE.md
```

---

## Generate a blockchain app

AGILANG can generate a complete configurable blockchain starter:

```bash
agi new my-chain --template blockchain
cd my-chain
agi run
agi run src/chain.agi
agi run src/beacon.agi
```

The generated project includes:

```text
src/main.agi
src/chain.agi
src/beacon.agi
src/staking.agi
src/network.agi
src/ethereum_clients.agi
src/ethereum_consensus.agi
config/genesis.json
config/network.json
config/rpc.json
config/beacon.json
config/ethereum-consensus-replica.json
config/ethereum-clients.json
config/wallets/wallets.example.json
storage/beacon.sqlite
docs/BLOCKCHAIN_RUNBOOK.md
docs/SBQ_BEACON_CHAIN_V21.md
docs/ETHEREUM_CONSENSUS_REPLICA_V20_2.md
```

Full blockchain generator guide:

```text
docs/BLOCKCHAIN_APP_GENERATOR.md
```

---

## Native SBQ Beacon commands

```bash
agi beacon capabilities
agi beacon init
agi beacon status
agi beacon validators
agi beacon produce-block
agi beacon attest
agi beacon finalize
agi beacon fork-choice
agi beacon simulate --validators 64 --epochs 10
```

The SBQ Beacon layer is for AGILANG/SBQ custom chains. It is not an Ethereum mainnet validator replacement.

---

## Ethereum runtime boundary

AGILANG supports three blockchain lanes:

| Mode | Consensus |
|---|---|
| SBQ native chain | Native SBQ Beacon or AGILANG PoS/DPoS/dev |
| Ethereum-derived private fork | Ethereum PoS replica by default |
| Ethereum mainnet connectivity | Real external Ethereum clients |
| Ethereum mainnet validation | Official Ethereum consensus/validator clients only |

AGILANG does not override live Ethereum mainnet consensus. Ethereum mainnet validation must remain external-client based unless full Ethereum consensus-spec compatibility, security review, and production hardening are completed.

---

## Documentation map

| Document | Purpose |
|---|---|
| `docs/GETTING_STARTED.md` | Beginner installation and first app guide |
| `docs/LANGUAGE_GUIDE.md` | AGILANG syntax and programming basics |
| `docs/CLI_REFERENCE.md` | Command-line guide |
| `docs/APPLICATIONS_AND_STARTERS.md` | Web, CMS, business, realtime, and blockchain starter overview |
| `docs/BLOCKCHAIN_APP_GENERATOR.md` | Step-by-step blockchain app generator guide |
| `docs/SBQ_BEACON_CHAIN_V21.md` | Native SBQ Beacon layer |
| `docs/ETHEREUM_CONSENSUS_REPLICA_V20_2.md` | Ethereum PoS replica private-fork profile |
| `docs/ETHEREUM_CLIENT_STACK_V20.md` | External Ethereum client orchestration |
| `docs-site/index.html` | Static HTML documentation landing page |

---

## Static HTML documentation site

A GitHub Pages-ready documentation landing page is included in:

```text
docs-site/index.html
```

Recommended GitHub Pages setup:

```text
Repository Settings -> Pages -> Deploy from branch -> main -> /docs-site
```

Use the HTML site as the public polished documentation homepage, while keeping Markdown docs for GitHub readers and contributors.

---

## Branches

| Branch | Purpose |
|---|---|
| `main` | AGILANG runtime, language docs, CLI, blockchain runtime, tests |
| `dev` | Active runtime/framework development |
| `blog` | Public CMS/blog/web app starter branch |
| `evm-chain-implementations` | EVM chain implementation track |

---

## Starter quality rule

No page should be a fake static template. Every visible section must be backed by a route, config, database query, seed/demo data file, or a proper empty state.
## Production boundary

AGILANG is suitable for local development, staging, private-fork simulation, application scaffolding, and AGILANG/SBQ chain implementation work. Before any public real-value chain launch, add independent security review, hardened networking, peer scoring, validator key isolation, validator penalty economics, DoS hardening, archive/indexer separation, long-running supervision, and production monitoring.
