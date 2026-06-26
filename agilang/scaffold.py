"""Project scaffolding for AGILANG apps.

The v1.9 scaffold is intentionally practical: `agi new my app` creates a
ready-to-run web project with HTTP routes, JSON APIs, static files, templates,
a realtime WebSocket example, tests, deployment notes, and a short runbook.
"""
from __future__ import annotations

import re
import shutil
import textwrap
from dataclasses import dataclass
from pathlib import Path


def slugify_project_name(raw: str) -> str:
    """Convert a user supplied app name into a safe directory/package slug."""
    name = raw.strip().replace("_", "-")
    name = re.sub(r"[^A-Za-z0-9\-\s]+", "", name)
    name = re.sub(r"[\s\-]+", "-", name).strip("-").lower()
    return name or "agilang-app"


def module_name(slug: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", slug).strip("_") or "agilang_app"


def titleize(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.replace("_", "-").split("-") if part) or "AGILANG App"


@dataclass
class ScaffoldResult:
    root: Path
    files: list[Path]
    template: str

    def as_dict(self) -> dict[str, object]:
        return {"root": str(self.root), "template": self.template, "files": [str(f) for f in self.files]}


def _write(path: Path, content: str, files: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
    files.append(path)


def _copy_vendor_runtime(root: Path, files: list[Path]) -> None:
    # Bundle the AGILANG runtime into generated apps for shared hosting.
    source = Path(__file__).resolve().parent
    target = root / "vendor" / "agilang"
    if target.exists():
        shutil.rmtree(target)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "build", "dist", "*.egg-info", "tests")
    shutil.copytree(source, target, ignore=ignore)
    _write(root / "vendor" / "README.md", '''
        # AGILANG Bundled Vendor Runtime

        This folder is intentionally shipped with generated AGILANG apps.

        Shared-hosting entrypoints such as `public_html/app.cgi`,
        `public_html/app.fcgi`, and `passenger_wsgi.py` load this local runtime
        first, so the app can run on cPanel/Plesk-style hosting without a global
        AGILANG installation.
        ''', files)
    files.append(target / "__init__.py")


def create_project(name: str, *, directory: str | Path | None = None, template: str = "web", force: bool = False) -> ScaffoldResult:
    """Create a new AGILANG project.

    Templates:
    - ``web`` / ``web-live``: full web starter with templates/static/API/realtime example.
    - ``api``: API-focused starter.
    - ``systems``: low-level networking + EVM systems starter.
    - ``zk``: zero-knowledge systems starter with circuits, commitments, Merkle proofs, and Schnorr demos.
    - ``blockchain``: full blockchain starter with PoS, mempool, fork choice, chain DB and EVM hooks.
    - ``basic``: minimal AGILANG CLI starter.
    """
    template = (template or "web").lower()
    if template in {"web-live", "web-ags", "ags", "reactive"}:
        template = "web"
    if template not in {"web", "api", "basic", "systems", "zk", "blockchain"}:
        raise ValueError("template must be one of: web, web-live, web-ags, ags, reactive, api, basic, systems, zk, blockchain")
    slug = slugify_project_name(name)
    title = titleize(slug)
    parent = Path(directory).expanduser().resolve() if directory else Path.cwd().resolve()
    root = parent / slug
    if root.exists() and any(root.iterdir()) and not force:
        raise FileExistsError(f"Directory exists and is not empty: {root}")
    files: list[Path] = []

    _write(root / "agilang.toml", f'''
        [project]
        name = "{slug}"
        version = "0.1.0"
        entry = "src/main.agi"
        template = "{template}"

        [runtime]
        mode = "hybrid"
        host = "127.0.0.1"
        port = 8000

        [native]
        prefer_prebuilt = true
        supported_platforms = ["linux-x86_64", "windows-x86_64", "macos-x86_64", "macos-arm64"]
        ''', files)

    _write(root / ".env.example", f'''
        APP_NAME="{title}"
        APP_ENV=local
        APP_SECRET=change-me-before-production
        APP_URL=http://127.0.0.1:8000
        AGILANG_RUNTIME_MODE=hybrid
        AGILANG_HOST=127.0.0.1
        AGILANG_PORT=8000
        ''', files)

    _write(root / ".gitignore", '''
        __pycache__/
        .pytest_cache/
        .agilang/
        build/
        dist/
        *.db
        *.sqlite
        .env
        node_modules/
        ''', files)

    if template == "basic":
        _write(root / "src/main.agi", f'''
            fn main() -> i32:
                print("Hello from {title}")
                return 0
            ''', files)
    elif template == "systems":
        _write(root / "src/main.agi", f'''
            fn main() -> i32:
                print("{title} systems starter")
                print("network", lowlevel_network_capabilities())
                print("evm", evm_capabilities())
                let frame = packet_json("app.ready", {{"name": "{slug}"}}, "systems")
                let event = packet_json_parse(frame)
                assert_eq(event["type"], "app.ready")
                let selector = evm_function_selector("transfer(address,uint256)")
                print("transfer selector", selector)
                return 0
            ''', files)
        _write(root / "src/network.agi", f'''
            fn main() -> i32:
                let udp = udp_socket("127.0.0.1", 0)
                let addr = udp.address
                udp.send_to("hello from {slug}", addr.host, addr.port)
                let received = udp.recv_from(1024, 2.0)
                print("udp received", received[0].decode("utf-8"))
                udp.close()
                return 0
            ''', files)
        _write(root / "src/evm.agi", f'''
            fn main() -> i32:
                let builder = evm_bytecode_builder()
                let code = builder.push(1).push(2).add().stop().hex()
                print("bytecode", code)
                print("disasm", evm_disassemble(code))
                return 0
            ''', files)
    elif template == "zk":
        _write(root / "src/main.agi", f'''
            fn main() -> i32:
                print("{title} zero-knowledge starter")
                print("zk", zk_capabilities())
                let commitment = zk_commit({{"account": "demo", "balance": 100}}, "starter-salt")
                assert_eq(zk_verify_commitment(commitment, {{"account": "demo", "balance": 100}}), True)
                let proof = zk_merkle_proof(["alice", "bob", "carol"], 1)
                assert_eq(zk_verify_merkle_proof("bob", proof["index"], proof["proof"], proof["root"]), True)
                print("commitment", commitment["commitment"])
                print("merkle root", proof["root"])
                return 0
            ''', files)
        _write(root / "src/circuit.agi", f'''
            fn main() -> i32:
                let circuit = zk_circuit("square_proof")
                circuit.var("secret", 12, public=False)
                circuit.var("square", 144, public=True)
                circuit.assert_mul("secret", "secret", "square")
                let check = circuit.check()
                print("circuit ok", check["ok"])
                print("public witness", circuit.public_witness())
                return 0
            ''', files)
        _write(root / "src/schnorr.agi", f'''
            fn main() -> i32:
                let key = zk_schnorr_keypair(2026)
                let proof = zk_schnorr_prove(key["secret"], "{slug}")
                print("verified", zk_schnorr_verify(proof, "{slug}"))
                return 0
            ''', files)
        _write(root / "docs/ZK_RUNBOOK.md", f'''
            # {title} ZK Runbook

            Run the starter:

            ```bash
            agi run
            agi run src/circuit.agi
            agi run src/schnorr.agi
            agi zk capabilities
            agi zk bridge-status
            ```

            This template uses AGILANG-native developer primitives: R1CS-style
            constraint checks, salted commitments, Merkle membership proofs, and
            Schnorr-style proof demos. For production SNARK/STARK proving, connect
            an audited external prover through `zk_external_engine()` or ship a
            precompiled native prover package.
            ''', files)

    elif template == "blockchain":
        _write(root / "src/main.agi", f'''
            fn main() -> i32:
                print("{title} blockchain starter")
                print("capabilities", blockchain_capabilities())
                let cfg = blockchain_config(chain_id=1900, name="{slug}", validators={{"alice": 60, "bob": 40}}, genesis_state={{"balances": {{"alice": 1000, "bob": 250}}}}, slot_seconds=1)
                let node = blockchain_node(cfg, "../storage/chain.sqlite", "alice-node")
                let tx = blockchain_transaction("alice", "bob", 25, nonce=1, gas_price=1)
                let added = node.submit_tx(tx)
                print("mempool add", added)
                let parent = node.head()
                let slot = parent["slot"] + 1
                let proposer = node.consensus.select_proposer(parent["hash"], slot)
                let produced = node.produce_and_import_block(proposer, slot)
                print("block", produced["block"]["height"], produced["block"]["hash"])
                print("status", node.status())
                return 0
            ''', files)
        _write(root / "src/chain.agi", f'''
            fn main() -> i32:
                let cfg = blockchain_config(chain_id=1900, name="{slug}", validators={{"alice": 70, "bob": 30}}, slot_seconds=1)
                let node = blockchain_node(cfg, "../storage/chain.sqlite", "validator-node")
                print("head", node.head())
                print("finalized", node.finalized_head())
                return 0
            ''', files)
        _write(root / "src/mempool.agi", f'''
            fn main() -> i32:
                let cfg = blockchain_config(chain_id=1900, name="{slug}", validators={{"alice": 100}})
                let node = blockchain_node(cfg, ":memory:", "mempool-node")
                let a = blockchain_transaction("alice", "bob", 5, nonce=1, gas_price=1)
                let b = blockchain_transaction("alice", "carol", 7, nonce=2, gas_price=2)
                print(node.submit_tx(a))
                print(node.submit_tx(b))
                print(node.mempool_status())
                return 0
            ''', files)
        _write(root / "src/devnet.agi", f'''
            fn main() -> i32:
                let cfg = blockchain_config(chain_id=1900, name="{slug}-devnet", validators={{"alice": 60, "bob": 40}}, slot_seconds=1)
                let net = blockchain_devnet(cfg, ["alice", "bob"])
                let tx = blockchain_transaction("alice", "bob", 10, nonce=1, gas_price=1)
                print("submit", net.submit_tx(tx))
                print("step", net.step())
                print("sync", net.sync_all())
                return 0
            ''', files)
        _write(root / "src/evm_contract.agi", f'''
            fn main() -> i32:
                let code = evm_bytecode_builder().push(42).push(0).mstore().push(32).push(0).return_().hex()
                let result = evm_execute(code)
                print("evm", result)
                return 0
            ''', files)
        _write(root / "config/validators.json", f'''
            {{
              "chain_id": 1900,
              "consensus": "pos",
              "available_consensus_modes": ["pos", "dpos", "dpo", "dev"],
              "validators": {{
                "alice": 60,
                "bob": 40
              }},
              "slot_seconds": 1,
              "finality_depth": 8,
              "block_gas_limit": 30000000
            }}
            ''', files)
        _write(root / "docs/BLOCKCHAIN_RUNBOOK.md", f'''
            # {title} Blockchain Runbook

            This starter is a configurable AGILANG private-chain/devnet framework.

            ## Start

            ```bash
            agi run
            agi run src/chain.agi
            agi run src/mempool.agi
            agi run src/devnet.agi
            agi run src/evm_contract.agi
            ```

            ## CLI tools

            ```bash
            agi blockchain capabilities
            agi blockchain demo
            agi blockchain simulate-consensus
            agi blockchain init-genesis --db storage/chain.sqlite --validator alice:60 --validator bob:40
            agi blockchain init-genesis --consensus dpo --validator alice:60 --validator bob:40
            agi blockchain mempool-demo --consensus pos --sender alice --to bob --value 10
            agi blockchain produce-block --consensus dev --validator alice --to bob --value 10
            agi blockchain devnet --consensus dpos --blocks 3
            ```

            ## Included modules

            - selectable Proof-of-Stake, DPoS/DPO and Dev consensus
            - proposer selection and block validation
            - optional mainnet-profile block-signature validation
            - mempool admission/replacement/ordering
            - canonical SQLite chain database
            - fork-choice and finality-depth marking
            - block production
            - in-process p2p/devnet sync
            - EVM execution hooks for contract deployment/calls

            ## Production boundary

            This is suitable for private-chain development, education, devnets,
            prototypes and framework extension. Before using it for public networks
            or real-value systems, add cryptographic validator keys/signatures,
            peer scoring, slashing, formal fork-choice review, DoS limits, network
            protocol hardening, database compaction, block pruning, state tries and
            independent security audits.
            ''', files)

    else:
        debug = "False" if template == "api" else "True"
        _write(root / "src/main.agi", f'''
            import os

            const APP_NAME = os.environ.get("APP_NAME", "{title}")
            const APP_URL = os.environ.get("APP_URL", "http://127.0.0.1:8000").rstrip("/")
            const DB_PATH = os.environ.get("DATABASE_PATH", "../storage/app.sqlite")

            fn db():
                ensure_dir("../storage")
                return sqlite_db(DB_PATH)

            fn migrate_app(app_db):
                app_db.execute("create table if not exists events (id integer primary key autoincrement, title text not null, status text not null default 'open', created_at text not null default current_timestamp)")
                let existing = app_db.one("select count(*) as total from events")
                if existing["total"] == 0:
                    app_db.execute("insert into events (title, status) values (?, ?)", ["Starter booted", "online"])

            fn create_app():
                let app_db = db()
                migrate_app(app_db)
                let app = web_app("{slug}", {debug})
                app.static("/assets", "../resources/assets")
                app.after(security_headers())

                fn home(request):
                    let view = render_ags("../resources/views/home.ags", {{"app_name": APP_NAME}})
                    return html_response(render_template("../resources/views/layout.ags", {{"title": view["meta"].get("title", APP_NAME), "seo": seo_tags(page_seo(view["meta"].get("title", APP_NAME), "/")), "body": view["body"]}}))

                fn dashboard(request):
                    let view = render_ags("../resources/views/dashboard.ags", {{"app_name": APP_NAME}})
                    return html_response(render_template("../resources/views/layout.ags", {{"title": view["meta"].get("title", APP_NAME), "seo": seo_tags(page_seo(view["meta"].get("title", APP_NAME), "/dashboard")), "body": view["body"]}}))

                fn health(request):
                    return json_response({{"ok": True, "app": "{slug}", "runtime": "agilang", "template": "ags"}})

                fn api_home_stats(request):
                    let events_count = app_db.one("select count(*) as total from events")["total"]
                    return json_response({{"users": 1, "items": events_count, "status": "online", "app": APP_NAME}})

                app.get("/", home, name="home")
                app.get("/dashboard", dashboard, name="dashboard")
                app.get("/health", health, name="health")
                app.get("/api/home-stats", api_home_stats, name="api.home_stats")
                return app

            fn page_seo(title, path):
                return {{"title": title, "description": "{title} is an AGILANG reactive AGS starter with live backend data.", "canonical": APP_URL + path, "site_name": APP_NAME, "type": "website", "robots": "index,follow", "twitter_card": "summary"}}

            fn main() -> i32:
                let app = create_app()
                let server = app.listen("127.0.0.1", 0)
                server.run_background()
                print("{title} dev check:", web_get(server.url + "/health"))
                server.stop()
                return 0
            ''', files)

        _write(root / "src/realtime.agi", f'''
            fn main() -> i32:
                let server = websocket_listen("127.0.0.1", 9001, "/realtime")

                fn on_message(client, message):
                    let event = json_event("app.message", {{"app": "{slug}", "text": message}}, "app.realtime")
                    server.broadcast(event)

                server.on_message(on_message)
                print("Realtime server for {title}: ws://127.0.0.1:9001/realtime")
                server.serve_forever()
                return 0
            ''', files)

        _write(root / "resources/views/layout.ags", '''
            <!doctype html>
            <html lang="en">
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <title>{{ title }}</title>
              {{{ seo }}}
              <link rel="stylesheet" href="/assets/css/app.css">
              <script src="/assets/js/ags-runtime.js" defer></script>
            </head>
            <body>
              {{{ body }}}
            </body>
            </html>
            ''', files)

        _write(root / "resources/views/home.ags", f'''
            @page title="{title}" seo_description="AGILANG reactive AGS starter with live backend data."
            @fetch stats from "/api/home-stats"
            @live stats from "/api/home-stats" every 5000

            <main class="shell hero">
              <p class="eyebrow">AGILANG AGS reactive starter</p>
              <h1>{{{{ app_name }}}}</h1>
              <p>This page is <code>resources/views/home.ags</code>. It updates backend data without a full browser refresh.</p>
              <div class="actions">
                <a class="button" href="/dashboard">Open dashboard</a>
                <a class="button secondary" href="/api/home-stats">Live JSON</a>
              </div>
              <section class="stats">
                <article><span>Users</span><strong>{{{{ stats.users }}}}</strong></article>
                <article><span>Items</span><strong>{{{{ stats.items }}}}</strong></article>
                <article><span>Status</span><strong>{{{{ stats.status }}}}</strong></article>
              </section>
            </main>
            ''', files)

        _write(root / "resources/views/dashboard.ags", f'''
            @page title="{title} Dashboard" seo_description="Live AGILANG dashboard using AGS templates."
            @fetch stats from "/api/home-stats"
            @live stats from "/api/home-stats" every 3000

            <main class="shell">
              <p class="eyebrow">Reactive dashboard</p>
              <h1>{{{{ app_name }}}} dashboard</h1>
              <p>The dashboard uses <code>@live stats</code> and automatic bindings like <code>{{{{ stats.items }}}}</code>.</p>
              <section class="card-grid">
                <article class="card"><span>App</span><strong>{{{{ stats.app }}}}</strong></article>
                <article class="card"><span>Items</span><strong>{{{{ stats.items }}}}</strong></article>
                <article class="card"><span>Status</span><strong>{{{{ stats.status }}}}</strong></article>
              </section>
            </main>
            ''', files)

        _write(root / "templates/home.html", f'''
            <main class="shell hero">
              <p class="eyebrow">AGILANG starter</p>
              <h1>{title}</h1>
              <p>Compatibility template alias for resources/views/home.ags.</p>
            </main>
            ''', files)

        _write(root / "templates/dashboard.html", f'''
            <main class="shell">
              <p class="eyebrow">Dashboard</p>
              <h1>{title} dashboard</h1>
              <p>Compatibility template alias for resources/views/dashboard.ags.</p>
            </main>
            ''', files)

        _write(root / "resources/assets/css/app.css", '''
            :root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, Arial, sans-serif; }
            * { box-sizing: border-box; }
            body { margin: 0; min-height: 100vh; background: radial-gradient(circle at top left, #123b64, #06111f 50%, #02050a); color: #eef7ff; }
            .shell { width: min(1040px, calc(100% - 32px)); margin: 0 auto; padding: 56px 0; }
            .hero { min-height: 100vh; display: grid; align-content: center; }
            .eyebrow { color: #59e0ff; letter-spacing: .14em; text-transform: uppercase; font-size: .78rem; font-weight: 800; }
            h1 { font-size: clamp(2.4rem, 8vw, 5.5rem); line-height: .95; margin: 0 0 18px; }
            p { color: #b8cadc; font-size: 1.1rem; max-width: 760px; line-height: 1.6; }
            code { color: #8ff7d2; }
            .actions, .stats, .card-grid { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 26px; }
            .button { background: #59e0ff; color: #02121f; padding: 13px 18px; border-radius: 999px; text-decoration: none; font-weight: 800; }
            .button.secondary { background: rgba(255,255,255,.1); color: #eef7ff; border: 1px solid rgba(255,255,255,.18); }
            .stats article, .card { min-width: 190px; background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.14); border-radius: 20px; padding: 20px; }
            .stats span, .card span { display: block; color: #b8cadc; margin-bottom: 8px; }
            .stats strong, .card strong { font-size: 1.8rem; }
            ''', files)

        _write(root / "public/css/app.css", '''
            @import url("/assets/css/app.css");
            ''', files)

        _write(root / "resources/assets/js/ags-runtime.js", '''
            (function () {
              function readPath(data, path) {
                return String(path || "").split(".").filter(Boolean).reduce(function (value, key) {
                  if (value && Object.prototype.hasOwnProperty.call(value, key)) return value[key];
                  return "";
                }, data);
              }
              async function updateElement(element, url) {
                const response = await fetch(url, { headers: { Accept: "application/json" } });
                const data = await response.json();
                const value = readPath(data, element.getAttribute("data-ags-path"));
                element.textContent = value == null ? "" : String(value);
              }
              function hydrate() {
                document.querySelectorAll("[data-ags-fetch]").forEach(function (element) {
                  updateElement(element, element.getAttribute("data-ags-fetch")).catch(function () {});
                });
                document.querySelectorAll("[data-ags-live]").forEach(function (element) {
                  const url = element.getAttribute("data-ags-live");
                  const every = Math.max(1000, Number(element.getAttribute("data-ags-every") || 5000));
                  updateElement(element, url).catch(function () {});
                  setInterval(function () { updateElement(element, url).catch(function () {}); }, every);
                });
              }
              if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hydrate);
              else hydrate();
            })();
            ''', files)

        _write(root / "public/js/app.js", '''
            import "/assets/js/ags-runtime.js";
            ''', files)

        _write(root / "storage/.gitkeep", "\n", files)

    _write(root / "tests/test_main.agi", '''
        import "../src/main.agi"

        fn main() -> i32:
            let app = create_app()
            let server = app.listen("127.0.0.1", 0)
            server.run_background()
            let body = web_get(server.url + "/health")
            assert_eq(body.find("ok") >= 0, True)
            server.stop()
            print("project tests passed")
            return 0
        ''', files)

    _write(root / "deployment/NGINX.md", f'''
        # Nginx deployment for {title}

        Development:

        ```bash
        agi serve src/main.agi --host 127.0.0.1 --port 8000
        agi run src/realtime.agi
        ```

        Reverse-proxy example:

        ```nginx
        server {{
            listen 80;
            server_name example.com;

            location / {{
                proxy_pass http://127.0.0.1:8000;
                proxy_set_header Host $host;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_set_header X-Forwarded-Proto $scheme;
            }}

            location /realtime {{
                proxy_pass http://127.0.0.1:9001;
                proxy_http_version 1.1;
                proxy_set_header Upgrade $http_upgrade;
                proxy_set_header Connection "upgrade";
                proxy_set_header Host $host;
            }}
        }}
        ```
        ''', files)

    _write(root / "deployment/CADDY.md", f'''
        # Caddy deployment for {title}

        ```caddyfile
        example.com {{
            reverse_proxy /realtime* 127.0.0.1:9001
            reverse_proxy 127.0.0.1:8000
        }}
        ```
        ''', files)

    if template != "basic":
        _copy_vendor_runtime(root, files)
        from .cgi_runtime import write_shared_hosting_files
        hosting = write_shared_hosting_files(root, entry="src/main.agi", target="public_html", mode="auto", force=True)
        files.extend(hosting.files)

    _write(root / "README.md", f'''
        # {title}

        Generated by **AGILANG v1.9.4 Reactive AGS Starter Edition**.

        ## Start the app

        ```bash
        cd {slug}
        agi run
        agi serve src/main.agi --host 127.0.0.1 --port 8000

        # Shortcut also supported:
        agi serve src/main.agi --8000
        ```

        Open: <http://127.0.0.1:8000>

        ## Start realtime transport

        In a second terminal:

        ```bash
        agi run src/realtime.agi
        ```

        Dashboard route: <http://127.0.0.1:8000/dashboard>

        ## Test

        ```bash
        agi test
        agi check src tests
        agi runtime platform-matrix
        agi runtime prebuilt-status
        agi runtime doctor
        agi hosting capabilities
        agi hosting doctor
        agi mobile platform-matrix
        agi mobile capabilities
        ```

        ## Generated structure

        ```text
        {slug}/
          agilang.toml
          src/main.agi
          src/realtime.agi
          resources/views/home.ags
          resources/views/dashboard.ags
          resources/views/layout.ags
          resources/assets/css/app.css
          resources/assets/js/ags-runtime.js
          vendor/agilang/
          storage/.gitkeep
          tests/test_main.agi
          public_html/.htaccess
          public_html/app.cgi
          public_html/app.fcgi
          passenger_wsgi.py
          deployment/NGINX.md
          deployment/CADDY.md
          deployment/CPANEL_PLESK_CGI_FASTCGI.md
        ```

        ## cPanel / Plesk shared hosting

        This project ships CGI/FastCGI entrypoints for Apache shared hosting:

        ```text
        public_html/.htaccess
        public_html/app.cgi
        public_html/app.fcgi
        passenger_wsgi.py
        ```

        Regenerate them at any time:

        ```bash
        agi hosting scaffold --mode auto --entry src/main.agi
        ```

        Use `public_html/` on cPanel, or copy the contents of `public_html/` into Plesk `httpdocs/`. Classic CGI works with only Python; FastCGI needs host support and optional `flup`.

        ## Cross-platform native runtime

        AGILANG loads native runtime artifacts in this order:

        1. Developer-supplied library path
        2. Cached installed runtime
        3. Bundled platform prebuilt runtime
        4. Local C compilation fallback

        Supported release targets are Linux x86_64, Windows x86_64, macOS x86_64, macOS arm64, Android arm64/x86_64, and iOS device/simulator bridge targets. Run:

        ```bash
        agi runtime platform-matrix
        agi mobile platform-matrix
        ```

        ## Mobile app support

        Generate a React Native/Expo client:

        ```bash
        agi react mobile {slug}-mobile
        ```

        Generate Android/iOS native bridge source for the AGILANG C runtime:

        ```bash
        agi mobile native-bridge {slug}-native --target both
        ```
        ''', files)

    return ScaffoldResult(root=root, files=files, template=template)
