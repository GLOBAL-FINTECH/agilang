"""AGILANG command line interface."""

from __future__ import annotations

import argparse
import builtins
import os
import platform
import json
import runpy
import subprocess
import sys
import textwrap
import types
from pathlib import Path

from . import __version__
from .checker import check_file
from .ast_nodes import ast_to_dict
from .backends import describe_backends
from .c_backend import compile_c, to_c_file
from .config import load_project_config
from .formatter import format_file
from .lexer import tokenize, tokens_as_table
from .parser import parse_file
from .typechecker import typecheck_file
from .std import load_std_globals
from .translator import AGILTranslator


PROJECT_MAIN = '''fn main() -> i32:
    print("Hello from AGILANG project")
    return 0
'''

PROJECT_TEST = '''import "../src/main.agi"

fn main() -> i32:
    assert_eq(1 + 1, 2)
    print("tests passed")
    return 0
'''


def _resolve_source(file: str | None) -> Path:
    if file is None:
        config = load_project_config()
        if config is None:
            raise FileNotFoundError("No file provided and no agilang.toml project was found.")
        path = config.entry_path
    else:
        path = Path(file).resolve()
    if not path.exists():
        raise FileNotFoundError(f"No such file: {path}")
    if path.suffix != ".agi":
        raise ValueError(f"Expected a .agi file, got: {path}")
    return path


def _execute_python(python_code: str, source_path: Path, dump: bool = False) -> int:
    if dump:
        sys.stderr.write("===== Transpiled Python code =====\n")
        sys.stderr.write(python_code)
        sys.stderr.write("\n=================================\n")
    exec_globals = load_std_globals()
    exec_globals.update(vars(builtins))
    module_name = "__agilang_main__"
    module = types.ModuleType(module_name)
    sys.modules[module_name] = module
    exec_globals["__name__"] = module_name
    exec_globals["__file__"] = str(source_path)
    module.__dict__.update(exec_globals)
    exec_globals = module.__dict__
    old_cwd = os.getcwd()
    try:
        os.chdir(str(source_path.parent))
        exec(compile(python_code, str(source_path), "exec"), exec_globals)
        maybe_main = exec_globals.get("main")
        if callable(maybe_main):
            result = maybe_main()
            return int(result or 0) if isinstance(result, int) else 0
        return 0
    finally:
        os.chdir(old_cwd)


def _run(args: argparse.Namespace) -> None:
    source_path = _resolve_source(args.file)
    if args.check:
        report = check_file(source_path)
        if report.diagnostics:
            print(report.format(), file=sys.stderr)
        if not report.ok:
            raise SystemExit(1)
    translator = AGILTranslator()
    python_code = translator.translate_file(source_path)
    raise SystemExit(_execute_python(python_code, source_path, args.dump))


def _check(args: argparse.Namespace) -> None:
    had_error = False
    files: list[Path] = []
    for item in args.files:
        path = Path(item)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.agi")))
        else:
            files.append(path)
    if not files:
        print("No .agi files found.")
        return
    for file in files:
        report = check_file(file.resolve())
        status = "OK" if report.ok else "ERROR"
        print(f"{status}: {file}")
        if report.diagnostics:
            print(report.format())
        had_error = had_error or not report.ok
    if had_error:
        raise SystemExit(1)


def _to_py(args: argparse.Namespace) -> None:
    source_path = _resolve_source(args.file)
    translator = AGILTranslator()
    python_code = translator.translate_file(source_path)
    if args.line_map:
        numbered = []
        for i, line in enumerate(python_code.splitlines(), start=1):
            numbered.append(f"{i:04d}: {line}")
        python_code = "\n".join(numbered) + "\n"
    if args.output:
        Path(args.output).write_text(python_code, encoding="utf-8")
    else:
        sys.stdout.write(python_code)


def _build(args: argparse.Namespace) -> None:
    """Create a self-contained Python launcher from AGILANG source."""
    source_path = _resolve_source(args.file)
    translator = AGILTranslator()
    python_code = translator.translate_file(source_path)
    output = Path(args.output or (source_path.with_suffix(".py"))).resolve()
    std_source = Path(__file__).with_name("std.py").read_text(encoding="utf-8")
    realtime_source = Path(__file__).with_name("realtime.py").read_text(encoding="utf-8")
    web_source = Path(__file__).with_name("web.py").read_text(encoding="utf-8")
    webrtc_source = Path(__file__).with_name("webrtc.py").read_text(encoding="utf-8")
    security_source = Path(__file__).with_name("security.py").read_text(encoding="utf-8")
    hybrid_source = Path(__file__).with_name("hybrid_runtime.py").read_text(encoding="utf-8")
    cgi_runtime_source = Path(__file__).with_name("cgi_runtime.py").read_text(encoding="utf-8")
    mobile_runtime_source = Path(__file__).with_name("mobile_runtime.py").read_text(encoding="utf-8")
    lowlevel_network_source = Path(__file__).with_name("lowlevel_network.py").read_text(encoding="utf-8")
    evm_source = Path(__file__).with_name("evm.py").read_text(encoding="utf-8")
    zk_source = Path(__file__).with_name("zk.py").read_text(encoding="utf-8")
    interop_source = Path(__file__).with_name("interop.py").read_text(encoding="utf-8")
    blockchain_source = Path(__file__).with_name("blockchain.py").read_text(encoding="utf-8")
    launcher = (
        f"# Generated by AGILANG {__version__}.\n"
        f"# Source: {source_path}\n"
        "import builtins as _builtins\n"
        "import sys as _sys\n"
        "import types as _types\n"
        "_AGI_PKG = _types.ModuleType('agilang')\n"
        "_AGI_PKG.__path__ = []\n"
        "_sys.modules.setdefault('agilang', _AGI_PKG)\n"
        "_STD = _types.ModuleType('agilang.std')\n"
        "_sys.modules['agilang.std'] = _STD\n"
        f"_STD_SOURCE = {std_source!r}\n"
        "exec(compile(_STD_SOURCE, 'agilang.std', 'exec'), _STD.__dict__)\n"
        "_REALTIME = _types.ModuleType('agilang.realtime')\n"
        "_sys.modules['agilang.realtime'] = _REALTIME\n"
        f"_REALTIME_SOURCE = {realtime_source!r}\n"
        "exec(compile(_REALTIME_SOURCE, 'agilang.realtime', 'exec'), _REALTIME.__dict__)\n"
        "_WEB = _types.ModuleType('agilang.web')\n"
        "_sys.modules['agilang.web'] = _WEB\n"
        f"_WEB_SOURCE = {web_source!r}\n"
        "exec(compile(_WEB_SOURCE, 'agilang.web', 'exec'), _WEB.__dict__)\n"
        "_WEBRTC = _types.ModuleType('agilang.webrtc')\n"
        "_sys.modules['agilang.webrtc'] = _WEBRTC\n"
        f"_WEBRTC_SOURCE = {webrtc_source!r}\n"
        "exec(compile(_WEBRTC_SOURCE, 'agilang.webrtc', 'exec'), _WEBRTC.__dict__)\n"
        "_SECURITY = _types.ModuleType('agilang.security')\n"
        "_sys.modules['agilang.security'] = _SECURITY\n"
        f"_SECURITY_SOURCE = {security_source!r}\n"
        "exec(compile(_SECURITY_SOURCE, 'agilang.security', 'exec'), _SECURITY.__dict__)\n"
        "_HYBRID = _types.ModuleType('agilang.hybrid_runtime')\n"
        "_sys.modules['agilang.hybrid_runtime'] = _HYBRID\n"
        f"_HYBRID_SOURCE = {hybrid_source!r}\n"
        "exec(compile(_HYBRID_SOURCE, 'agilang.hybrid_runtime', 'exec'), _HYBRID.__dict__)\n"
        "_CGI_RUNTIME = _types.ModuleType('agilang.cgi_runtime')\n"
        "_sys.modules['agilang.cgi_runtime'] = _CGI_RUNTIME\n"
        "# CGI runtime is not embedded in standalone builds because it depends on compiler modules.\n"
        "_LOWLEVEL_NETWORK = _types.ModuleType('agilang.lowlevel_network')\n"
        "_sys.modules['agilang.lowlevel_network'] = _LOWLEVEL_NETWORK\n"
        f"_LOWLEVEL_NETWORK_SOURCE = {lowlevel_network_source!r}\n"
        "exec(compile(_LOWLEVEL_NETWORK_SOURCE, 'agilang.lowlevel_network', 'exec'), _LOWLEVEL_NETWORK.__dict__)\n"
        "_EVM = _types.ModuleType('agilang.evm')\n"
        "_sys.modules['agilang.evm'] = _EVM\n"
        f"_EVM_SOURCE = {evm_source!r}\n"
        "exec(compile(_EVM_SOURCE, 'agilang.evm', 'exec'), _EVM.__dict__)\n"
        "_ZK = _types.ModuleType('agilang.zk')\n"
        "_sys.modules['agilang.zk'] = _ZK\n"
        f"_ZK_SOURCE = {zk_source!r}\n"
        "exec(compile(_ZK_SOURCE, 'agilang.zk', 'exec'), _ZK.__dict__)\n"
        "_INTEROP = _types.ModuleType('agilang.interop')\n"
        "_sys.modules['agilang.interop'] = _INTEROP\n"
        f"_INTEROP_SOURCE = {interop_source!r}\n"
        "exec(compile(_INTEROP_SOURCE, 'agilang.interop', 'exec'), _INTEROP.__dict__)\n"
        "_BLOCKCHAIN = _types.ModuleType('agilang.blockchain')\n"
        "_sys.modules['agilang.blockchain'] = _BLOCKCHAIN\n"
        f"_BLOCKCHAIN_SOURCE = {blockchain_source!r}\n"
        "exec(compile(_BLOCKCHAIN_SOURCE, 'agilang.blockchain', 'exec'), _BLOCKCHAIN.__dict__)\n"
        "_GLOBALS = _STD.__dict__['load_std_globals']()\n"
        "_GLOBALS.update(vars(_builtins))\n"
        "_GLOBALS['__name__'] = '__main__'\n"
        "_GLOBALS['__file__'] = __file__\n"
        f"_CODE = {python_code!r}\n"
        f"exec(compile(_CODE, {str(source_path)!r}, 'exec'), _GLOBALS)\n"
        "if callable(_GLOBALS.get('main')):\n"
        "    raise SystemExit(_GLOBALS['main']() or 0)\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(launcher, encoding="utf-8")
    print(f"Built {output}")


def _serve(args: argparse.Namespace) -> None:
    """Serve a WebApp exported from an AGILANG source file."""
    source_path = _resolve_source(args.file)
    translator = AGILTranslator()
    python_code = translator.translate_file(source_path)
    exec_globals = load_std_globals()
    exec_globals.update(vars(builtins))
    exec_globals["__name__"] = "__agilang_web__"
    exec_globals["__file__"] = str(source_path)
    old_cwd = os.getcwd()
    try:
        os.chdir(str(source_path.parent))
        exec(compile(python_code, str(source_path), "exec"), exec_globals)
        app = exec_globals.get("app") or exec_globals.get("application")
        create_app = exec_globals.get("create_app")
        if app is None and callable(create_app):
            app = create_app()
        if app is None and callable(exec_globals.get("main")):
            app = exec_globals["main"]()
        if app is None or not hasattr(app, "listen"):
            raise RuntimeError("No WebApp found. Define global `app`, `application`, `create_app()`, or return an app from main().")
        server = app.listen(args.host, args.port)
        print(f"Serving {source_path} on {server.url}")
        server.serve_forever()
    finally:
        os.chdir(old_cwd)


def _read_env_file(root: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    env_path = root / ".env"
    if not env_path.exists():
        env_path = root / ".env.example"
    if not env_path.exists():
        return values
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _db_config(args: argparse.Namespace, include_database: bool = True) -> dict[str, object]:
    root = Path(getattr(args, "root", ".") or ".").resolve()
    env = _read_env_file(root)
    def pick(name: str, default: str = "") -> str:
        return str(os.environ.get(name) or env.get(name) or default)
    cfg: dict[str, object] = {
        "host": pick("MYSQL_HOST", "127.0.0.1"),
        "port": int(pick("MYSQL_PORT", "3306")),
        "user": pick("MYSQL_USER", "root"),
        "password": pick("MYSQL_PASSWORD", ""),
        "charset": "utf8mb4",
    }
    database = pick("MYSQL_DATABASE", "devapp_blog")
    if include_database:
        cfg["database"] = database
    return cfg


def _mysql_connect(args: argparse.Namespace, include_database: bool = True):
    try:
        import pymysql
        from pymysql.cursors import DictCursor
    except ImportError as exc:
        raise SystemExit("PyMySQL is required. Run: pip install -r requirements.txt") from exc
    return pymysql.connect(cursorclass=DictCursor, autocommit=False, **_db_config(args, include_database=include_database))


def _split_sql(sql: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False
    prev = ""
    for ch in sql:
        if ch == "'" and prev != "\\" and not in_double:
            in_single = not in_single
        elif ch == '"' and prev != "\\" and not in_single:
            in_double = not in_double
        if ch == ";" and not in_single and not in_double:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(ch)
        prev = ch
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def _migration_dir(args: argparse.Namespace) -> Path:
    root = Path(getattr(args, "root", ".") or ".").resolve()
    path = Path(getattr(args, "path", "") or root / "database" / "migrations")
    if not path.is_absolute():
        path = root / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ensure_migrations_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS agilang_migrations ("
            "id INT PRIMARY KEY AUTO_INCREMENT,"
            "migration VARCHAR(255) NOT NULL UNIQUE,"
            "batch INT NOT NULL DEFAULT 1,"
            "migrated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        )


def _db_create(args: argparse.Namespace) -> None:
    cfg = _db_config(args, include_database=False)
    database = str(os.environ.get("MYSQL_DATABASE") or _read_env_file(Path(getattr(args, "root", ".") or ".").resolve()).get("MYSQL_DATABASE") or "devapp_blog")
    conn = _mysql_connect(args, include_database=False)
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        print(f"Database ready: {database}")
    finally:
        conn.close()


def _db_migrate(args: argparse.Namespace) -> None:
    conn = _mysql_connect(args)
    try:
        _ensure_migrations_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT migration FROM agilang_migrations")
            applied = {row["migration"] for row in cur.fetchall()}
            cur.execute("SELECT COALESCE(MAX(batch), 0) + 1 AS batch FROM agilang_migrations")
            batch = int(cur.fetchone()["batch"])
        files = sorted(_migration_dir(args).glob("*.sql"))
        pending = [file for file in files if file.name not in applied]
        if not pending:
            print("Nothing to migrate.")
            return
        for file in pending:
            sql = file.read_text(encoding="utf-8")
            with conn.cursor() as cur:
                for statement in _split_sql(sql):
                    cur.execute(statement)
                cur.execute("INSERT INTO agilang_migrations (migration, batch) VALUES (%s, %s)", (file.name, batch))
            print(f"Migrated: {file.name}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _db_status(args: argparse.Namespace) -> None:
    conn = _mysql_connect(args)
    try:
        _ensure_migrations_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT migration FROM agilang_migrations")
            applied = {row["migration"] for row in cur.fetchall()}
        for file in sorted(_migration_dir(args).glob("*.sql")):
            state = "ran" if file.name in applied else "pending"
            print(f"{state:8} {file.name}")
    finally:
        conn.close()


def _db_refresh(args: argparse.Namespace) -> None:
    if getattr(args, "refresh_action", "migrate") != "migrate":
        raise SystemExit("Use: agi db refresh migrate")
    conn = _mysql_connect(args)
    try:
        with conn.cursor() as cur:
            cur.execute("SET FOREIGN_KEY_CHECKS=0")
            cur.execute("SHOW TABLES")
            key = f"Tables_in_{_db_config(args).get('database')}"
            for row in cur.fetchall():
                table = row.get(key) or next(iter(row.values()))
                cur.execute(f"DROP TABLE IF EXISTS `{table}`")
            cur.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()
        print("Database refreshed.")
    finally:
        conn.close()
    _db_migrate(args)


def _timestamp_name(action: str, table: str) -> str:
    from datetime import datetime
    safe_action = "".join(ch if ch.isalnum() else "_" for ch in action.lower()).strip("_")
    safe_table = "".join(ch if ch.isalnum() else "_" for ch in table.lower()).strip("_")
    return datetime.now().strftime("%Y%m%d%H%M%S") + f"_{safe_action}_{safe_table}.sql"


def _db_table(args: argparse.Namespace) -> None:
    migrations = _migration_dir(args)
    table = args.table
    command = args.table_command
    if command == "create":
        columns = [part.strip() for part in (args.columns or "").split(",") if part.strip()]
        ddl_columns = ["  id INT PRIMARY KEY AUTO_INCREMENT"]
        for column in columns:
            if ":" in column:
                name, spec = column.split(":", 1)
                ddl_columns.append(f"  {name.strip()} {spec.strip()}")
            else:
                ddl_columns.append(f"  {column}")
        ddl_columns.append("  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")
        ddl_columns.append("  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
        sql = f"CREATE TABLE IF NOT EXISTS {table} (\n" + ",\n".join(ddl_columns) + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;\n"
        path = migrations / _timestamp_name("create", table)
    elif command == "add-column":
        sql = f"ALTER TABLE {table} ADD COLUMN {args.column} {args.definition};\n"
        path = migrations / _timestamp_name(f"add_{args.column}_to", table)
    elif command == "drop-column":
        sql = f"ALTER TABLE {table} DROP COLUMN {args.column};\n"
        path = migrations / _timestamp_name(f"drop_{args.column}_from", table)
    elif command == "drop":
        sql = f"DROP TABLE IF EXISTS {table};\n"
        path = migrations / _timestamp_name("drop", table)
    else:
        raise SystemExit("Unknown table command")
    path.write_text(sql, encoding="utf-8")
    print(f"Created migration: {path}")


def _db_cmd(args: argparse.Namespace) -> None:
    if args.db_command == "create":
        _db_create(args)
    elif args.db_command == "migrate":
        _db_migrate(args)
    elif args.db_command == "status":
        _db_status(args)
    elif args.db_command in {"refresh", "refresh-migrate"}:
        _db_refresh(args)
    elif args.db_command == "table":
        _db_table(args)
    else:
        raise SystemExit("Unknown db command")

def _fmt(args: argparse.Namespace) -> None:
    changed = False
    for item in args.files:
        path = Path(item)
        files = sorted(path.rglob("*.agi")) if path.is_dir() else [path]
        for file in files:
            original = file.read_text(encoding="utf-8")
            formatted = format_file(file, write=args.write)
            if formatted != original:
                changed = True
                print(f"FORMATTED: {file}" if args.write else f"WOULD FORMAT: {file}")
                if not args.write:
                    print(formatted)
            else:
                print(f"OK: {file}")
    if changed and args.check:
        raise SystemExit(1)


def _new(args: argparse.Namespace) -> None:
    from .scaffold import create_project

    raw_name = " ".join(args.name) if isinstance(args.name, list) else str(args.name)
    result = create_project(raw_name, directory=args.dir, template=args.template, force=args.force)
    print(f"Created AGILANG {result.template} project: {result.root}")
    print("Generated files:")
    for file in result.files:
        try:
            rel = file.relative_to(result.root)
        except ValueError:
            rel = file
        print(f"  - {rel}")
    print("\nNext commands:")
    print(f"  cd {result.root.name}")
    print("  agi run")
    if result.template in {"web", "api"}:
        print("  agi serve src/main.agi --host 127.0.0.1 --port 8000")
        print("  agi run src/realtime.agi")
    elif result.template == "ai":
        print("  agi serve src/main.agi --host 127.0.0.1 --port 8000")
        print("  agi run src/model.agi")
    elif result.template == "systems":
        print("  agi run src/network.agi")
        print("  agi run src/evm.agi")
    elif result.template == "zk":
        print("  agi run src/circuit.agi")
        print("  agi run src/schnorr.agi")
    elif result.template == "blockchain":
        print("  agi run src/chain.agi")
        print("  agi run src/mempool.agi")
        print("  agi run src/devnet.agi")
        print("  agi blockchain demo")


def _slug_name(raw: str) -> str:
    value = raw.strip().replace("_", "-")
    value = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in value)
    value = "-".join(part for part in value.lower().split("-") if part)
    return value or "page"


def _snake_name(raw: str) -> str:
    return _slug_name(raw).replace("-", "_")


def _title_name(raw: str) -> str:
    return " ".join(part.capitalize() for part in _slug_name(raw).split("-"))


def _write_new_file(path: Path, content: str, force: bool = False) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"File exists: {path}. Use --force to overwrite.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
    print(f"Created {path}")


def _make_page(args: argparse.Namespace) -> None:
    slug = _slug_name(args.name)
    title = _title_name(slug)
    path = Path(args.dir or ".").resolve() / "resources" / "views" / f"{slug}.ags"
    _write_new_file(path, f'''
        @page title="{title}" seo_description="{title} page for this AGILANG app." robots="index,follow"
        @layout "layout.ags"

        <section class="dashboard">
          <div>
            <p class="eyebrow">{title}</p>
            <h1>{title}</h1>
            <p>Edit this AGS page at <code>resources/views/{slug}.ags</code>.</p>
          </div>
        </section>
        ''', args.force)
    print("\nRoute guidance:")
    print(f"  fn { _snake_name(slug) }_page(request):")
    print(f"      let view = render_ags(\"../resources/views/{slug}.ags\", {{}})")
    print(f"      return html_response(layout(view[\"meta\"].get(\"title\", \"{title}\"), view[\"body\"], current_account(request), \"{slug}\"))")
    print(f"  app.get(\"/{slug}\", { _snake_name(slug) }_page)")


def _make_component(args: argparse.Namespace) -> None:
    slug = _slug_name(args.name)
    component = "".join(part.capitalize() for part in slug.split("-"))
    path = Path(args.dir or ".").resolve() / "resources" / "views" / "components" / f"{slug}.ags"
    _write_new_file(path, f'''
        @component {component}

        <article class="{slug}">
          <span>{{{{ label }}}}</span>
          <strong>{{{{ value }}}}</strong>
        </article>
        ''', args.force)
    print("\nUsage:")
    print(f"  render_ags(\"../resources/views/components/{slug}.ags\", {{\"label\": \"Total\", \"value\": 42}})[\"body\"]")


def _make_api(args: argparse.Namespace) -> None:
    slug = _slug_name(args.name)
    snake = _snake_name(slug)
    path = Path(args.dir or ".").resolve() / "src" / "api" / f"{snake}.agi"
    route = "/" + slug
    if not route.startswith("/api/"):
        route = "/api/" + slug
    _write_new_file(path, f'''
        fn api_{snake}(request):
            return json_response({{
                "ok": True,
                "name": "{slug}",
                "status": "online"
            }})

        # Add this to create_app() in src/main.agi:
        # app.get("{route}", api_{snake})
        ''', args.force)
    print("\nRoute guidance:")
    print(f"  import \"src/api/{snake}.agi\"")
    print(f"  app.get(\"{route}\", api_{snake})")


def _test_examples(args: argparse.Namespace) -> None:
    examples_dir = Path(args.dir).resolve()
    files = sorted(examples_dir.glob("*.agi"))
    failures = 0
    for file in files:
        if args.skip_network and file.name in {"web_scrape.agi", "react_mobile_backend.agi"}:
            print(f"SKIP {file.name}: network/long-running example")
            continue
        try:
            translator = AGILTranslator()
            code = translator.translate_file(file)
            _execute_python(code, file, dump=False)
            print(f"PASS {file.name}")
        except Exception as exc:
            failures += 1
            print(f"FAIL {file.name}: {exc}")
    if failures:
        raise SystemExit(1)


def _doctor(args: argparse.Namespace) -> None:
    print(f"AGILANG: {__version__}")
    print(f"Python: {platform.python_version()} ({sys.executable})")
    print(f"Platform: {platform.platform()}")
    for package in ["requests", "numpy", "sklearn", "matplotlib"]:
        try:
            __import__(package)
            print(f"optional {package}: installed")
        except Exception:
            print(f"optional {package}: not installed")


def _repl(args: argparse.Namespace) -> None:
    print(f"AGILANG {__version__} REPL. Type :quit to exit. Use Python-like expressions or AGILANG let/fn lines.")
    translator = AGILTranslator()
    env = load_std_globals()
    env.update(vars(builtins))
    buffer: list[str] = []
    while True:
        prompt = "... " if buffer else "agi> "
        try:
            line = input(prompt)
        except EOFError:
            print()
            break
        if line.strip() in {":q", ":quit", "exit"}:
            break
        buffer.append(line)
        if line.strip().endswith(":"):
            continue
        try:
            src = "\n".join(buffer)
            py = translator.translate(src)
            try:
                compiled_expr = compile(py.strip(), "<repl>", "eval")
            except SyntaxError:
                exec(compile(py, "<repl>", "exec"), env)
            else:
                result = eval(compiled_expr, env)
                if result is not None:
                    print(repr(result))
        except Exception as exc:
            print(f"error: {exc}")
        finally:
            buffer.clear()



def _tokens(args: argparse.Namespace) -> None:
    source_path = _resolve_source(args.file)
    source = source_path.read_text(encoding="utf-8")
    print(tokens_as_table(tokenize(source, source_path)))


def _test_project(args: argparse.Namespace) -> None:
    root = Path(args.dir).resolve() if args.dir else Path.cwd().resolve()
    tests_dir = root / "tests"
    if not tests_dir.exists():
        print(f"No tests directory found: {tests_dir}")
        return
    files = sorted(tests_dir.rglob("*.agi"))
    if not files:
        print(f"No .agi tests found in: {tests_dir}")
        return
    failures = 0
    for file in files:
        try:
            report = check_file(file) if args.check else None
            if report is not None and not report.ok:
                failures += 1
                print(f"FAIL {file}: static check failed")
                print(report.format())
                continue
            code = AGILTranslator().translate_file(file)
            _execute_python(code, file, dump=False)
            print(f"PASS {file}")
        except Exception as exc:
            failures += 1
            print(f"FAIL {file}: {exc}")
    if failures:
        raise SystemExit(1)



def _ast_cmd(args: argparse.Namespace) -> None:
    source_path = _resolve_source(args.file)
    program = parse_file(source_path)
    payload = ast_to_dict(program)
    if args.pretty:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, separators=(",", ":")))


def _typecheck(args: argparse.Namespace) -> None:
    had_error = False
    for item in args.files:
        path = Path(item)
        files = sorted(path.rglob("*.agi")) if path.is_dir() else [path]
        for file in files:
            report = typecheck_file(file.resolve())
            print(f"{'OK' if report.ok else 'ERROR'}: {file}")
            if report.diagnostics:
                print(report.format())
            had_error = had_error or not report.ok
    if had_error:
        raise SystemExit(1)


def _to_c(args: argparse.Namespace) -> None:
    source_path = _resolve_source(args.file)
    result = to_c_file(source_path)
    if result.diagnostics and (not result.ok or args.diagnostics):
        print(result.format(), file=sys.stderr)
    if not result.ok:
        raise SystemExit(1)
    if args.output:
        output = Path(args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result.c_source, encoding="utf-8")
        print(f"Generated {output}")
    else:
        sys.stdout.write(result.c_source)


def _native_build(args: argparse.Namespace) -> None:
    source_path = _resolve_source(args.file)
    c_result = to_c_file(source_path)
    if not c_result.ok:
        print(c_result.format(), file=sys.stderr)
        raise SystemExit(1)
    c_file = Path(args.c_output or source_path.with_suffix(".c")).resolve()
    exe_default = source_path.with_suffix(".exe" if platform.system().lower().startswith("win") else "")
    output = Path(args.output or exe_default).resolve()
    c_file.parent.mkdir(parents=True, exist_ok=True)
    c_file.write_text(c_result.c_source, encoding="utf-8")
    proc = compile_c(c_file, output, cc=args.cc)
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    print(f"Built native executable: {output}")


def _pkg_cmd(args: argparse.Namespace) -> None:
    from . import pkg as pkgmod

    if args.pkg_command == "init":
        manifest = pkgmod.init_project(args.name, Path(args.dir).resolve() if args.dir else None)
        print(f"Initialized package: {manifest.project.get('name')} at {manifest.root}")
    elif args.pkg_command == "add":
        manifest = pkgmod.add_dependency(args.name, args.spec)
        print(f"Added dependency {args.name} = {args.spec}")
    elif args.pkg_command == "remove":
        pkgmod.remove_dependency(args.name)
        print(f"Removed dependency {args.name}")
    elif args.pkg_command == "list":
        print(pkgmod.list_dependencies())
    elif args.pkg_command == "install":
        installed = pkgmod.install_dependencies()
        if installed:
            for item in installed:
                print(f"Installed metadata: {item}")
        else:
            print("No dependencies to install.")
    elif args.pkg_command == "pack":
        target = pkgmod.pack_project(out=Path(args.output).resolve() if args.output else None)
        print(f"Packed project: {target}")
    else:
        raise ValueError("Unknown pkg command")


def _react_cmd(args: argparse.Namespace) -> None:
    from .react_support import create_react_mobile_project, create_react_web_project, write_react_sdk

    if args.react_command == "web":
        target = create_react_web_project(args.name, args.dir)
        print(f"Created React web project: {target}")
    elif args.react_command == "mobile":
        target = create_react_mobile_project(args.name, args.dir)
        print(f"Created React Native/Expo project: {target}")
    elif args.react_command == "sdk":
        target = write_react_sdk(args.dir)
        print(f"Wrote AGILANG React SDK: {target}")
    else:
        raise ValueError("Unknown react command")


def _runtime_cmd(args: argparse.Namespace) -> None:
    from .hybrid_runtime import (
        compile_native_runtime,
        native_runtime_status,
        native_runtime_available,
        native_prebuilt_status,
        native_prebuilt_runtime_install,
        native_platform_matrix,
    )

    if args.runtime_command == "status":
        print(json.dumps(native_runtime_status(build=args.build), indent=2))
    elif args.runtime_command == "build":
        result = compile_native_runtime(args.output, cc=args.cc)
        print(json.dumps(result.as_dict(), indent=2))
        if not result.ok:
            raise SystemExit(result.returncode or 1)
    elif args.runtime_command == "doctor":
        installed = native_prebuilt_runtime_install(None)
        payload = native_runtime_status(build=False)
        payload["prebuilt_installed"] = str(installed) if installed else None
        payload["available"] = native_runtime_available()
        if not payload.get("available") and payload.get("compiler"):
            payload["build"] = compile_native_runtime().as_dict()
            payload["available_after_build"] = native_runtime_available()
        print(json.dumps(payload, indent=2))
        if not (payload.get("available") or payload.get("available_after_build")):
            raise SystemExit(1)
    elif args.runtime_command == "prebuilt-status":
        print(json.dumps(native_prebuilt_status(), indent=2))
    elif args.runtime_command == "install-prebuilt":
        installed = native_prebuilt_runtime_install(args.output)
        payload = {"ok": installed is not None, "installed_library_path": str(installed) if installed else None}
        print(json.dumps(payload, indent=2))
        if installed is None:
            raise SystemExit(1)
    elif args.runtime_command == "platform-matrix":
        print(json.dumps(native_platform_matrix(), indent=2))
    else:
        raise ValueError("Unknown runtime command")




def _mobile_cmd(args: argparse.Namespace) -> None:
    from .mobile_runtime import (
        mobile_runtime_matrix,
        mobile_runtime_capabilities,
        mobile_runtime_doctor,
        create_mobile_native_bridge,
    )

    if args.mobile_command == "platform-matrix":
        print(json.dumps(mobile_runtime_matrix(), indent=2))
    elif args.mobile_command == "capabilities":
        print(json.dumps(mobile_runtime_capabilities(), indent=2))
    elif args.mobile_command == "doctor":
        print(json.dumps(mobile_runtime_doctor(), indent=2))
    elif args.mobile_command == "native-bridge":
        result = create_mobile_native_bridge(args.name, directory=args.dir, target=args.target, force=args.force)
        print(f"Created AGILANG mobile native bridge: {result.root}")
        for file in result.files:
            try:
                rel = file.relative_to(result.root)
            except ValueError:
                rel = file
            print(f"  - {rel}")
    else:
        raise ValueError("Unknown mobile command")

def _hosting_cmd(args: argparse.Namespace) -> None:
    from .cgi_runtime import discover_shared_hosting, shared_hosting_capabilities, write_shared_hosting_files

    if args.hosting_command == "capabilities":
        print(json.dumps(shared_hosting_capabilities(), indent=2))
    elif args.hosting_command == "doctor":
        payload = discover_shared_hosting()
        payload["capabilities"] = shared_hosting_capabilities()
        print(json.dumps(payload, indent=2))
    elif args.hosting_command == "scaffold":
        result = write_shared_hosting_files(root=args.root, entry=args.entry, target=args.target, mode=args.mode, force=args.force)
        print(f"Created AGILANG shared-hosting files in: {result.target}")
        for file in result.files:
            try:
                rel = file.relative_to(result.root)
            except ValueError:
                rel = file
            print(f"  - {rel}")
        print("\nUpload public_html/ for cPanel, or copy it to httpdocs/ on Plesk.")
    else:
        raise ValueError("Unknown hosting command")


def _net_cmd(args: argparse.Namespace) -> None:
    from .lowlevel_network import lowlevel_network_capabilities, packet_json, packet_json_parse

    if args.net_command == "capabilities":
        print(json.dumps(lowlevel_network_capabilities(), indent=2))
    elif args.net_command == "doctor":
        payload = {"capabilities": lowlevel_network_capabilities()}
        probe = packet_json("net.doctor", {"ok": True}, "agilang")
        payload["packet_framing_roundtrip"] = packet_json_parse(probe)
        print(json.dumps(payload, indent=2))
    else:
        raise ValueError("Unknown net command")


def _evm_cmd(args: argparse.Namespace) -> None:
    from .evm import (
        evm_capabilities, evm_function_selector, evm_disassemble,
        evm_contract_call_data, evm_abi_encode, evm_abi_decode, evm_bytecode_builder,
        evm_execute, evm_simulate_call, evm_estimate_gas, evm_trace, evm_legacy_unsigned_tx,
        evm_external_engine,
    )

    if args.evm_command == "capabilities":
        print(json.dumps(evm_capabilities(), indent=2))
    elif args.evm_command == "selector":
        print(evm_function_selector(args.signature))
    elif args.evm_command == "calldata":
        types = [x.strip() for x in (args.types or "").split(",") if x.strip()]
        values = [x.strip() for x in (args.values or "").split(",") if x.strip()]
        print(evm_contract_call_data(args.signature, types, values))
    elif args.evm_command == "abi-encode":
        types = [x.strip() for x in args.types.split(",") if x.strip()]
        values = [x.strip() for x in args.values.split(",") if x.strip()]
        print(evm_abi_encode(types, values))
    elif args.evm_command == "abi-decode":
        types = [x.strip() for x in args.types.split(",") if x.strip()]
        print(json.dumps(evm_abi_decode(types, args.data), indent=2))
    elif args.evm_command == "disasm":
        print(json.dumps(evm_disassemble(args.bytecode), indent=2))
    elif args.evm_command == "run":
        print(json.dumps(evm_execute(args.bytecode, args.calldata, args.gas, trace=args.trace), indent=2))
    elif args.evm_command == "simulate-call":
        storage = json.loads(args.storage) if args.storage else None
        print(json.dumps(evm_simulate_call(args.bytecode, args.calldata, storage=storage, gas=args.gas, trace=args.trace), indent=2))
    elif args.evm_command == "estimate-gas":
        print(evm_estimate_gas(args.bytecode, args.calldata, gas_limit=args.gas))
    elif args.evm_command == "trace":
        print(json.dumps(evm_trace(args.bytecode, args.calldata, args.gas), indent=2))
    elif args.evm_command == "unsigned-tx":
        print(json.dumps(evm_legacy_unsigned_tx(args.nonce, args.gas_price, args.gas_limit, args.to, args.value, args.data, args.chain_id), indent=2))
    elif args.evm_command == "external-engine":
        print(json.dumps(evm_external_engine(args.name), indent=2))
    elif args.evm_command == "build-demo":
        code = evm_bytecode_builder().push(1).push(2).add().stop().hex()
        print(json.dumps({"bytecode": code, "disassembly": evm_disassemble(code), "result": evm_execute(code)}, indent=2))
    else:
        raise ValueError("Unknown evm command")



def _zk_cmd(args: argparse.Namespace) -> None:
    from .zk import (
        zk_capabilities,
        zk_bridge_status,
        zk_commit,
        zk_verify_commitment,
        zk_merkle_proof,
        zk_verify_merkle_proof,
        zk_circuit,
        zk_schnorr_keypair,
        zk_schnorr_prove,
        zk_schnorr_verify,
        zk_demo_payload,
    )

    if args.zk_command == "capabilities":
        print(json.dumps(zk_capabilities(), indent=2))
    elif args.zk_command == "bridge-status":
        print(json.dumps(zk_bridge_status(), indent=2))
    elif args.zk_command == "commit":
        payload = zk_commit(args.value, args.salt)
        print(json.dumps(payload, indent=2))
    elif args.zk_command == "verify-commit":
        ok = zk_verify_commitment(args.commitment, args.value, args.salt)
        print(json.dumps({"ok": ok}, indent=2))
    elif args.zk_command == "merkle-demo":
        leaves = [x.strip() for x in args.leaves.split(",") if x.strip()]
        proof = zk_merkle_proof(leaves, args.index)
        proof["verified"] = zk_verify_merkle_proof(proof["leaf"], proof["index"], proof["proof"], proof["root"])
        print(json.dumps(proof, indent=2))
    elif args.zk_command == "schnorr-demo":
        key = zk_schnorr_keypair(args.secret)
        proof = zk_schnorr_prove(key["secret"], args.message)
        print(json.dumps({"public": key["public"], "proof": proof, "verified": zk_schnorr_verify(proof, args.message)}, indent=2))
    elif args.zk_command == "circuit-demo":
        circuit = zk_circuit("square_demo")
        circuit.var("x", args.x, public=False)
        circuit.var("y", args.x * args.x, public=True)
        circuit.assert_mul("x", "x", "y")
        print(json.dumps({"r1cs": circuit.to_r1cs_dict(), "check": circuit.check(), "public_witness": circuit.public_witness()}, indent=2))
    elif args.zk_command == "demo":
        print(json.dumps(zk_demo_payload(), indent=2))
    else:
        raise ValueError("Unknown zk command")

def _systems_cmd(args: argparse.Namespace) -> None:
    from .interop import systems_capabilities, python_package_status, interop_capabilities

    if args.systems_command == "capabilities":
        print(json.dumps(systems_capabilities(), indent=2))
    elif args.systems_command == "doctor":
        payload = systems_capabilities()
        payload["python_optional_packages"] = python_package_status(["requests", "Crypto", "web3", "eth_abi", "py_ecc"])
        print(json.dumps(payload, indent=2))
    elif args.systems_command == "interop":
        print(json.dumps(interop_capabilities(), indent=2))
    else:
        raise ValueError("Unknown systems command")


def _blockchain_cmd(args: argparse.Namespace) -> None:
    from .blockchain import (
        blockchain_capabilities, blockchain_config, blockchain_devnet, blockchain_demo, blockchain_consensus_simulation,
        blockchain_node, blockchain_transaction, blockchain_merkle_root,
    )

    if args.blockchain_command == "capabilities":
        print(json.dumps(blockchain_capabilities(), indent=2))
    elif args.blockchain_command == "demo":
        print(json.dumps(blockchain_demo(), indent=2))
    elif args.blockchain_command == "simulate-consensus":
        print(json.dumps(blockchain_consensus_simulation(), indent=2))
    elif args.blockchain_command == "init-genesis":
        validators = {}
        for item in args.validator or []:
            name, _, stake = item.partition(":")
            validators[name or "validator"] = int(stake or "100")
        cfg = blockchain_config(chain_id=args.chain_id, name=args.name, validators=validators or None, consensus_mode=args.consensus)
        node = blockchain_node(cfg, db_path=args.db)
        payload = {"config": cfg.as_dict(), "genesis": node.export_genesis(), "status": node.status()}
        print(json.dumps(payload, indent=2))
    elif args.blockchain_command == "mempool-demo":
        cfg = blockchain_config(chain_id=args.chain_id, name=args.name, validators={"alice": 60, "bob": 40}, consensus_mode=args.consensus)
        node = blockchain_node(cfg, db_path=args.db)
        tx = blockchain_transaction(args.sender, args.to, args.value, nonce=args.nonce, gas_price=args.gas_price)
        print(json.dumps({"submit": node.submit_tx(tx), "mempool": node.mempool_status()}, indent=2))
    elif args.blockchain_command == "produce-block":
        cfg = blockchain_config(chain_id=args.chain_id, name=args.name, validators={args.validator: 100}, consensus_mode=args.consensus)
        node = blockchain_node(cfg, db_path=args.db)
        tx = blockchain_transaction(args.validator, args.to, args.value, nonce=args.nonce, gas_price=args.gas_price)
        node.submit_tx(tx)
        parent = node.head()
        slot = args.slot or (int(parent.get("slot", 0)) + 1)
        expected = node.consensus.select_proposer(parent["hash"], slot)
        block = node.produce_block(validator=expected, slot=slot)
        result = node.import_block(block)
        print(json.dumps({"expected_proposer": expected, "block": block, "import": result, "status": node.status()}, indent=2))
    elif args.blockchain_command == "devnet":
        validators = {"alice": 60, "bob": 40, "carol": 25}
        cfg = blockchain_config(chain_id=args.chain_id, name=args.name, validators=validators, slot_seconds=1, consensus_mode=args.consensus)
        net = blockchain_devnet(cfg, validators=list(validators.keys()))
        tx = blockchain_transaction("alice", "bob", args.value, nonce=1, gas_price=1)
        net.submit_tx(tx)
        steps = []
        for _ in range(args.blocks):
            steps.append(net.step())
        print(json.dumps({"devnet": net.status(), "produced": [{"height": s["block"]["height"], "hash": s["block"]["hash"], "proposer": s["proposer"]} for s in steps]}, indent=2))
    elif args.blockchain_command == "merkle-root":
        values = [v.strip() for v in args.values.split(",") if v.strip()]
        print(blockchain_merkle_root(values))
    else:
        raise ValueError("Unknown blockchain command")

def _lsp(args: argparse.Namespace) -> None:
    from .lsp import run_stdio_server

    run_stdio_server()


def _backends(args: argparse.Namespace) -> None:
    print(describe_backends())

def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agilang", description="AGILANG production language toolkit")
    parser.add_argument("--version", action="version", version=f"AGILANG {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run", help="Check, transpile, and run an AGILANG file")
    p.add_argument("file", nargs="?", help=".agi file. Defaults to [project].entry in agilang.toml")
    p.add_argument("--dump", action="store_true", help="Print generated Python before running")
    p.add_argument("--check", action="store_true", help="Run static checks before execution")
    p.set_defaults(func=_run)

    p = sub.add_parser("check", help="Static-check one file or directory")
    p.add_argument("files", nargs="+", help=".agi files or directories")
    p.set_defaults(func=_check)

    p = sub.add_parser("to-py", help="Transpile an AGILANG file to Python")
    p.add_argument("file")
    p.add_argument("-o", "--output")
    p.add_argument("--line-map", action="store_true", help="Prefix generated lines with numbers for debugging")
    p.set_defaults(func=_to_py)

    p = sub.add_parser("build", help="Build a standalone Python launcher from AGILANG source")
    p.add_argument("file")
    p.add_argument("-o", "--output")
    p.set_defaults(func=_build)

    p = sub.add_parser("fmt", help="Format AGILANG files")
    p.add_argument("files", nargs="+")
    p.add_argument("-w", "--write", action="store_true", help="Write changes in place")
    p.add_argument("--check", action="store_true", help="Fail if formatting would change files")
    p.set_defaults(func=_fmt)

    p = sub.add_parser("new", help="Create a new AGILANG project. Defaults to a full web starter.")
    p.add_argument("name", nargs="+", help="Project name. Multi-word names are accepted: agi new test app two")
    p.add_argument("--template", choices=["web", "web-live", "api", "ai", "basic", "systems", "zk", "blockchain"], default="web", help="Starter template to generate")
    p.add_argument("--dir", help="Parent directory for the generated project")
    p.add_argument("--force", action="store_true", help="Allow writing into an existing project directory")
    p.set_defaults(func=_new)

    p = sub.add_parser("make:page", help="Create a SEO-ready AGS page under resources/views")
    p.add_argument("name", help="Page name, for example pricing")
    p.add_argument("--dir", help="Project root. Defaults to current directory")
    p.add_argument("--force", action="store_true", help="Overwrite an existing generated page")
    p.set_defaults(func=_make_page)

    p = sub.add_parser("make:component", help="Create an AGS component under resources/views/components")
    p.add_argument("name", help="Component name, for example stat-card")
    p.add_argument("--dir", help="Project root. Defaults to current directory")
    p.add_argument("--force", action="store_true", help="Overwrite an existing generated component")
    p.set_defaults(func=_make_component)

    p = sub.add_parser("make:api", help="Create an AGILANG JSON API handler snippet under src/api")
    p.add_argument("name", help="API name, for example home-stats")
    p.add_argument("--dir", help="Project root. Defaults to current directory")
    p.add_argument("--force", action="store_true", help="Overwrite an existing generated API file")
    p.set_defaults(func=_make_api)

    p = sub.add_parser("test-examples", help="Run bundled examples")
    p.add_argument("--dir", default=str(Path(__file__).resolve().parent.parent / "examples"))
    p.add_argument("--skip-network", action="store_true", default=True)
    p.set_defaults(func=_test_examples)

    p = sub.add_parser("test", help="Run .agi files in the project tests directory")
    p.add_argument("--dir", help="Project root. Defaults to current directory")
    p.add_argument("--check", action="store_true", default=True, help="Run static checks before test execution")
    p.set_defaults(func=_test_project)

    p = sub.add_parser("tokens", help="Print AGILANG lexical tokens for a source file")
    p.add_argument("file")
    p.set_defaults(func=_tokens)

    p = sub.add_parser("ast", help="Parse an AGILANG file and print the compiler AST as JSON")
    p.add_argument("file")
    p.add_argument("--pretty", action="store_true", default=True, help="Pretty-print JSON output")
    p.set_defaults(func=_ast_cmd)

    p = sub.add_parser("typecheck", help="Run the AST-level type checker")
    p.add_argument("files", nargs="+", help=".agi files or directories")
    p.set_defaults(func=_typecheck)

    p = sub.add_parser("to-c", help="Compile AGILANG source to native C source")
    p.add_argument("file")
    p.add_argument("-o", "--output")
    p.add_argument("--diagnostics", action="store_true", help="Print backend diagnostics even when generation succeeds")
    p.set_defaults(func=_to_c)

    p = sub.add_parser("native-build", help="Build a native executable through the C backend and GCC/Clang")
    p.add_argument("file")
    p.add_argument("-o", "--output")
    p.add_argument("--c-output", help="Where to write generated C before compilation")
    p.add_argument("--cc", default="gcc", help="C compiler command, default: gcc")
    p.set_defaults(func=_native_build)

    p = sub.add_parser("backends", help="List supported and planned compiler backends")
    p.set_defaults(func=_backends)

    p = sub.add_parser("lsp", help="Start the AGILANG language server over stdio")
    p.set_defaults(func=_lsp)

    pkg = sub.add_parser("pkg", help="Manage AGILANG package metadata and dependencies")
    pkg_sub = pkg.add_subparsers(dest="pkg_command", required=True)
    p_init = pkg_sub.add_parser("init", help="Initialize agilang.toml and lock file")
    p_init.add_argument("--name")
    p_init.add_argument("--dir")
    p_init.set_defaults(func=_pkg_cmd)
    p_add = pkg_sub.add_parser("add", help="Add a dependency")
    p_add.add_argument("name")
    p_add.add_argument("spec", help="Version, path:../lib, or git+https://... reference")
    p_add.set_defaults(func=_pkg_cmd)
    p_remove = pkg_sub.add_parser("remove", help="Remove a dependency")
    p_remove.add_argument("name")
    p_remove.set_defaults(func=_pkg_cmd)
    p_list = pkg_sub.add_parser("list", help="List dependencies")
    p_list.set_defaults(func=_pkg_cmd)
    p_install = pkg_sub.add_parser("install", help="Create/update .agilang/deps metadata and lock file")
    p_install.set_defaults(func=_pkg_cmd)
    p_pack = pkg_sub.add_parser("pack", help="Package current project into .agipkg archive")
    p_pack.add_argument("-o", "--output")
    p_pack.set_defaults(func=_pkg_cmd)

    db = sub.add_parser("db", help="MySQL database automation: create, migrate, refresh, status, table migrations")
    db.add_argument("--root", default=".", help="Project root containing .env and database/migrations")
    db.add_argument("--path", default="", help="Migration directory, default database/migrations")
    db_sub = db.add_subparsers(dest="db_command", required=True)
    p_db_create = db_sub.add_parser("create", help="Create the configured MySQL database")
    p_db_create.set_defaults(func=_db_cmd)
    p_db_migrate = db_sub.add_parser("migrate", help="Run pending SQL migrations")
    p_db_migrate.set_defaults(func=_db_cmd)
    p_db_status = db_sub.add_parser("status", help="Show migration status")
    p_db_status.set_defaults(func=_db_cmd)
    p_db_refresh = db_sub.add_parser("refresh", help="Drop all tables, then optionally migrate")
    p_db_refresh.add_argument("refresh_action", nargs="?", default="migrate", choices=["migrate"], help="Use: agi db refresh migrate")
    p_db_refresh.set_defaults(func=_db_cmd)
    p_db_refresh_migrate = db_sub.add_parser("refresh-migrate", help="Drop all tables and rerun migrations")
    p_db_refresh_migrate.set_defaults(refresh_action="migrate", func=_db_cmd)
    db_table = db_sub.add_parser("table", help="Create editable table/column migration files")
    db_table_sub = db_table.add_subparsers(dest="table_command", required=True)
    p_table_create = db_table_sub.add_parser("create", help="Create a table migration")
    p_table_create.add_argument("table")
    p_table_create.add_argument("--columns", default="", help='Comma list, e.g. "post_id:int not null,body:text not null"')
    p_table_create.set_defaults(func=_db_cmd)
    p_table_add = db_table_sub.add_parser("add-column", help="Create an add-column migration")
    p_table_add.add_argument("table")
    p_table_add.add_argument("column")
    p_table_add.add_argument("definition", help='SQL definition, e.g. "varchar(190) null"')
    p_table_add.set_defaults(func=_db_cmd)
    p_table_drop_col = db_table_sub.add_parser("drop-column", help="Create a drop-column migration")
    p_table_drop_col.add_argument("table")
    p_table_drop_col.add_argument("column")
    p_table_drop_col.set_defaults(func=_db_cmd)
    p_table_drop = db_table_sub.add_parser("drop", help="Create a drop-table migration")
    p_table_drop.add_argument("table")
    p_table_drop.set_defaults(func=_db_cmd)

    react = sub.add_parser("react", help="Create React web/mobile clients and TypeScript SDK")
    react_sub = react.add_subparsers(dest="react_command", required=True)
    p_web = react_sub.add_parser("web", help="Create a Vite React web client wired to AGILANG realtime")
    p_web.add_argument("name")
    p_web.add_argument("--dir", help="Parent directory")
    p_web.set_defaults(func=_react_cmd)
    p_mobile = react_sub.add_parser("mobile", help="Create a React Native/Expo mobile client wired to AGILANG realtime")
    p_mobile.add_argument("name")
    p_mobile.add_argument("--dir", help="Parent directory")
    p_mobile.set_defaults(func=_react_cmd)
    p_sdk = react_sub.add_parser("sdk", help="Write agilangClient.ts into a directory")
    p_sdk.add_argument("dir")
    p_sdk.set_defaults(func=_react_cmd)

    runtime = sub.add_parser("runtime", help="Build and inspect the AGILANG/AGILAB native C + Python hybrid web runtime")
    runtime_sub = runtime.add_subparsers(dest="runtime_command", required=True)
    p_status = runtime_sub.add_parser("status", help="Show native runtime paths, ABI status, and capabilities")
    p_status.add_argument("--build", action="store_true", help="Build the native runtime before reporting status")
    p_status.set_defaults(func=_runtime_cmd)
    p_build = runtime_sub.add_parser("build", help="Compile the native C HTTP/WebSocket runtime as a shared library")
    p_build.add_argument("-o", "--output", help="Output directory for the shared library")
    p_build.add_argument("--cc", help="C compiler command, for example gcc or clang")
    p_build.set_defaults(func=_runtime_cmd)
    p_doctor = runtime_sub.add_parser("doctor", help="Build, load, and self-test the native runtime bridge")
    p_doctor.set_defaults(func=_runtime_cmd)
    p_prebuilt_status = runtime_sub.add_parser("prebuilt-status", help="Show bundled precompiled native runtime artifacts for this platform")
    p_prebuilt_status.set_defaults(func=_runtime_cmd)
    p_install_prebuilt = runtime_sub.add_parser("install-prebuilt", help="Install the bundled precompiled native runtime into the runtime cache/build directory")
    p_install_prebuilt.add_argument("-o", "--output", help="Output directory for the installed shared library")
    p_install_prebuilt.set_defaults(func=_runtime_cmd)
    p_platform_matrix = runtime_sub.add_parser("platform-matrix", help="Show cross-platform native runtime support for Linux, Windows, macOS, Android, and iOS")
    p_platform_matrix.set_defaults(func=_runtime_cmd)


    mobile = sub.add_parser("mobile", help="Inspect and generate Android/iOS AGILANG mobile native runtime bridge files")
    mobile_sub = mobile.add_subparsers(dest="mobile_command", required=True)
    p_mobile_matrix = mobile_sub.add_parser("platform-matrix", help="Show Android/iOS native bridge targets and bundled artifact availability")
    p_mobile_matrix.set_defaults(func=_mobile_cmd)
    p_mobile_caps = mobile_sub.add_parser("capabilities", help="Show AGILANG mobile app/runtime capabilities")
    p_mobile_caps.set_defaults(func=_mobile_cmd)
    p_mobile_doctor = mobile_sub.add_parser("doctor", help="Detect local React Native/Android/iOS build tools")
    p_mobile_doctor.set_defaults(func=_mobile_cmd)
    p_mobile_bridge = mobile_sub.add_parser("native-bridge", help="Generate Android/iOS native bridge source for a mobile app")
    p_mobile_bridge.add_argument("name", help="Bridge project name")
    p_mobile_bridge.add_argument("--dir", help="Parent directory")
    p_mobile_bridge.add_argument("--target", choices=["android", "ios", "both"], default="both")
    p_mobile_bridge.add_argument("--force", action="store_true")
    p_mobile_bridge.set_defaults(func=_mobile_cmd)

    hosting = sub.add_parser("hosting", help="Generate and inspect cPanel/Plesk CGI/FastCGI shared-hosting deployment files")
    hosting_sub = hosting.add_subparsers(dest="hosting_command", required=True)
    p_host_caps = hosting_sub.add_parser("capabilities", help="Show AGILANG CGI/FastCGI/WSGI shared-hosting capabilities")
    p_host_caps.set_defaults(func=_hosting_cmd)
    p_host_doctor = hosting_sub.add_parser("doctor", help="Detect current shared-hosting environment and supported modes")
    p_host_doctor.set_defaults(func=_hosting_cmd)
    p_host_scaffold = hosting_sub.add_parser("scaffold", help="Write public_html/app.cgi, app.fcgi, .htaccess and passenger_wsgi.py")
    p_host_scaffold.add_argument("--root", help="Project root. Defaults to current directory")
    p_host_scaffold.add_argument("--entry", default="src/main.agi", help="AGILANG web app entry file")
    p_host_scaffold.add_argument("--target", default="public_html", help="Target document-root folder, default public_html")
    p_host_scaffold.add_argument("--mode", choices=["auto", "cgi", "fastcgi", "passenger"], default="auto", help="Shared-hosting mode")
    p_host_scaffold.add_argument("--force", action="store_true", default=True, help="Allow overwriting generated hosting files")
    p_host_scaffold.set_defaults(func=_hosting_cmd)

    net = sub.add_parser("net", help="Low-level TCP/UDP/packet/gossip networking tools")
    net_sub = net.add_subparsers(dest="net_command", required=True)
    p_net_caps = net_sub.add_parser("capabilities", help="Show low-level networking capabilities")
    p_net_caps.set_defaults(func=_net_cmd)
    p_net_doctor = net_sub.add_parser("doctor", help="Run low-level networking packet/framing diagnostics")
    p_net_doctor.set_defaults(func=_net_cmd)

    evm = sub.add_parser("evm", help="EVM/blockchain tooling: selectors, ABI, bytecode, JSON-RPC helpers")
    evm_sub = evm.add_subparsers(dest="evm_command", required=True)
    p_evm_caps = evm_sub.add_parser("capabilities", help="Show EVM tooling capabilities")
    p_evm_caps.set_defaults(func=_evm_cmd)
    p_evm_selector = evm_sub.add_parser("selector", help="Compute a 4-byte EVM function selector")
    p_evm_selector.add_argument("signature", help="Example: transfer(address,uint256)")
    p_evm_selector.set_defaults(func=_evm_cmd)
    p_evm_calldata = evm_sub.add_parser("calldata", help="Build call data for static ABI args")
    p_evm_calldata.add_argument("signature")
    p_evm_calldata.add_argument("--types", default="", help="Comma-separated static ABI types")
    p_evm_calldata.add_argument("--values", default="", help="Comma-separated values")
    p_evm_calldata.set_defaults(func=_evm_cmd)
    p_evm_abi = evm_sub.add_parser("abi-encode", help="ABI encode static and dynamic args")
    p_evm_abi.add_argument("types", help="Comma-separated ABI types")
    p_evm_abi.add_argument("values", help="Comma-separated values")
    p_evm_abi.set_defaults(func=_evm_cmd)
    p_evm_decode = evm_sub.add_parser("abi-decode", help="ABI decode static/dynamic return data")
    p_evm_decode.add_argument("types", help="Comma-separated ABI types")
    p_evm_decode.add_argument("data", help="0x-prefixed ABI data")
    p_evm_decode.set_defaults(func=_evm_cmd)
    p_evm_disasm = evm_sub.add_parser("disasm", help="Disassemble EVM bytecode")
    p_evm_disasm.add_argument("bytecode")
    p_evm_disasm.set_defaults(func=_evm_cmd)
    p_evm_run = evm_sub.add_parser("run", help="Execute EVM bytecode locally with gas accounting")
    p_evm_run.add_argument("bytecode")
    p_evm_run.add_argument("--calldata", default="0x")
    p_evm_run.add_argument("--gas", type=int, default=10000000)
    p_evm_run.add_argument("--trace", action="store_true")
    p_evm_run.set_defaults(func=_evm_cmd)
    p_evm_call = evm_sub.add_parser("simulate-call", help="Run contract code with optional storage JSON")
    p_evm_call.add_argument("bytecode")
    p_evm_call.add_argument("--calldata", default="0x")
    p_evm_call.add_argument("--storage", default="")
    p_evm_call.add_argument("--gas", type=int, default=10000000)
    p_evm_call.add_argument("--trace", action="store_true")
    p_evm_call.set_defaults(func=_evm_cmd)
    p_evm_gas = evm_sub.add_parser("estimate-gas", help="Estimate local execution gas")
    p_evm_gas.add_argument("bytecode")
    p_evm_gas.add_argument("--calldata", default="0x")
    p_evm_gas.add_argument("--gas", type=int, default=10000000)
    p_evm_gas.set_defaults(func=_evm_cmd)
    p_evm_trace = evm_sub.add_parser("trace", help="Return opcode-level execution trace")
    p_evm_trace.add_argument("bytecode")
    p_evm_trace.add_argument("--calldata", default="0x")
    p_evm_trace.add_argument("--gas", type=int, default=10000000)
    p_evm_trace.set_defaults(func=_evm_cmd)
    p_evm_tx = evm_sub.add_parser("unsigned-tx", help="Build an unsigned legacy/EIP-155 transaction payload")
    p_evm_tx.add_argument("--nonce", type=int, required=True)
    p_evm_tx.add_argument("--gas-price", type=int, required=True)
    p_evm_tx.add_argument("--gas-limit", type=int, required=True)
    p_evm_tx.add_argument("--to", required=True)
    p_evm_tx.add_argument("--value", type=int, default=0)
    p_evm_tx.add_argument("--data", default="0x")
    p_evm_tx.add_argument("--chain-id", type=int, default=None)
    p_evm_tx.set_defaults(func=_evm_cmd)
    p_evm_ext = evm_sub.add_parser("external-engine", help="Detect optional audited EVM engines for interop")
    p_evm_ext.add_argument("name", nargs="?", default="auto")
    p_evm_ext.set_defaults(func=_evm_cmd)
    p_evm_demo = evm_sub.add_parser("build-demo", help="Build, disassemble, and execute a tiny EVM bytecode demo")
    p_evm_demo.set_defaults(func=_evm_cmd)


    zk = sub.add_parser("zk", help="Zero-knowledge tooling: circuits, commitments, Merkle proofs, Schnorr demos, prover bridges")
    zk_sub = zk.add_subparsers(dest="zk_command", required=True)
    p_zk_caps = zk_sub.add_parser("capabilities", help="Show ZK engine capabilities")
    p_zk_caps.set_defaults(func=_zk_cmd)
    p_zk_bridge = zk_sub.add_parser("bridge-status", help="Detect optional external ZK prover/verifier tools")
    p_zk_bridge.set_defaults(func=_zk_cmd)
    p_zk_commit = zk_sub.add_parser("commit", help="Create a salted hash commitment")
    p_zk_commit.add_argument("value")
    p_zk_commit.add_argument("--salt")
    p_zk_commit.set_defaults(func=_zk_cmd)
    p_zk_verify_commit = zk_sub.add_parser("verify-commit", help="Verify a salted hash commitment")
    p_zk_verify_commit.add_argument("commitment")
    p_zk_verify_commit.add_argument("value")
    p_zk_verify_commit.add_argument("--salt", required=True)
    p_zk_verify_commit.set_defaults(func=_zk_cmd)
    p_zk_merkle = zk_sub.add_parser("merkle-demo", help="Build and verify a Merkle membership proof")
    p_zk_merkle.add_argument("--leaves", default="alice,bob,carol")
    p_zk_merkle.add_argument("--index", type=int, default=1)
    p_zk_merkle.set_defaults(func=_zk_cmd)
    p_zk_schnorr = zk_sub.add_parser("schnorr-demo", help="Create and verify a Schnorr-style proof demo")
    p_zk_schnorr.add_argument("--secret", type=int, default=12345)
    p_zk_schnorr.add_argument("--message", default="agilang")
    p_zk_schnorr.set_defaults(func=_zk_cmd)
    p_zk_circuit = zk_sub.add_parser("circuit-demo", help="Build and check a tiny square circuit")
    p_zk_circuit.add_argument("--x", type=int, default=7)
    p_zk_circuit.set_defaults(func=_zk_cmd)
    p_zk_demo = zk_sub.add_parser("demo", help="Run all local ZK demos")
    p_zk_demo.set_defaults(func=_zk_cmd)

    systems = sub.add_parser("systems", help="General systems-language capability and interop diagnostics")
    systems_sub = systems.add_subparsers(dest="systems_command", required=True)
    p_sys_caps = systems_sub.add_parser("capabilities", help="Show AGILANG general systems capabilities")
    p_sys_caps.set_defaults(func=_systems_cmd)
    p_sys_doctor = systems_sub.add_parser("doctor", help="Detect optional Python/C package bridge capabilities")
    p_sys_doctor.set_defaults(func=_systems_cmd)
    p_sys_interop = systems_sub.add_parser("interop", help="Show Python/C interop strategy")
    p_sys_interop.set_defaults(func=_systems_cmd)

    blockchain = sub.add_parser("blockchain", help="Full blockchain framework: PoS/DPoS/Dev consensus, chain DB, mempool, fork-choice and devnet tools")
    blockchain_sub = blockchain.add_subparsers(dest="blockchain_command", required=True)
    p_bc_caps = blockchain_sub.add_parser("capabilities", help="Show blockchain framework capabilities")
    p_bc_caps.set_defaults(func=_blockchain_cmd)
    p_bc_demo = blockchain_sub.add_parser("demo", help="Run a complete blockchain devnet/block production demo")
    p_bc_demo.set_defaults(func=_blockchain_cmd)
    p_bc_sim = blockchain_sub.add_parser("simulate-consensus", help="Run PoS, DPoS/DPO, Dev and mainnet-profile simulations")
    p_bc_sim.set_defaults(func=_blockchain_cmd)
    p_bc_genesis = blockchain_sub.add_parser("init-genesis", help="Create a chain config, genesis block and SQLite canonical DB")
    p_bc_genesis.add_argument("--db", default=":memory:", help="SQLite chain database path")
    p_bc_genesis.add_argument("--chain-id", type=int, default=1900)
    p_bc_genesis.add_argument("--name", default="agilang-chain")
    p_bc_genesis.add_argument("--consensus", default="pos", choices=["pos", "dpos", "dpo", "dev"], help="Consensus mode")
    p_bc_genesis.add_argument("--validator", action="append", help="Validator stake entry, e.g. alice:100. Repeatable.")
    p_bc_genesis.set_defaults(func=_blockchain_cmd)
    p_bc_mempool = blockchain_sub.add_parser("mempool-demo", help="Submit a transaction into the managed mempool")
    p_bc_mempool.add_argument("--db", default=":memory:")
    p_bc_mempool.add_argument("--chain-id", type=int, default=1900)
    p_bc_mempool.add_argument("--name", default="agilang-chain")
    p_bc_mempool.add_argument("--consensus", default="pos", choices=["pos", "dpos", "dpo", "dev"], help="Consensus mode")
    p_bc_mempool.add_argument("--sender", default="alice")
    p_bc_mempool.add_argument("--to", default="bob")
    p_bc_mempool.add_argument("--value", type=int, default=10)
    p_bc_mempool.add_argument("--nonce", type=int, default=1)
    p_bc_mempool.add_argument("--gas-price", type=int, default=1)
    p_bc_mempool.set_defaults(func=_blockchain_cmd)
    p_bc_block = blockchain_sub.add_parser("produce-block", help="Produce and import one PoS block")
    p_bc_block.add_argument("--db", default=":memory:")
    p_bc_block.add_argument("--chain-id", type=int, default=1900)
    p_bc_block.add_argument("--name", default="agilang-chain")
    p_bc_block.add_argument("--consensus", default="pos", choices=["pos", "dpos", "dpo", "dev"], help="Consensus mode")
    p_bc_block.add_argument("--validator", default="alice")
    p_bc_block.add_argument("--to", default="bob")
    p_bc_block.add_argument("--value", type=int, default=10)
    p_bc_block.add_argument("--nonce", type=int, default=1)
    p_bc_block.add_argument("--gas-price", type=int, default=1)
    p_bc_block.add_argument("--slot", type=int)
    p_bc_block.set_defaults(func=_blockchain_cmd)
    p_bc_devnet = blockchain_sub.add_parser("devnet", help="Run an in-process multi-validator p2p devnet simulation")
    p_bc_devnet.add_argument("--chain-id", type=int, default=1900)
    p_bc_devnet.add_argument("--name", default="agilang-devnet")
    p_bc_devnet.add_argument("--consensus", default="pos", choices=["pos", "dpos", "dpo", "dev"], help="Consensus mode")
    p_bc_devnet.add_argument("--blocks", type=int, default=2)
    p_bc_devnet.add_argument("--value", type=int, default=25)
    p_bc_devnet.set_defaults(func=_blockchain_cmd)
    p_bc_merkle = blockchain_sub.add_parser("merkle-root", help="Compute a Merkle root for comma-separated values")
    p_bc_merkle.add_argument("values", help="Comma-separated values")
    p_bc_merkle.set_defaults(func=_blockchain_cmd)

    p = sub.add_parser("serve", help="Serve an AGILANG WebApp over HTTP")
    p.add_argument("file")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.set_defaults(func=_serve)

    p = sub.add_parser("doctor", help="Print environment diagnostics")
    p.set_defaults(func=_doctor)

    p = sub.add_parser("repl", help="Start an interactive AGILANG REPL")
    p.set_defaults(func=_repl)
    return parser


def _normalize_argv(argv: list[str] | None) -> list[str]:
    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and raw[0] == "serve":
        normalized: list[str] = []
        for token in raw:
            # Developer convenience: `agi serve src/main.agi --7000` means `--port 7000`.
            if token.startswith("--") and token[2:].isdigit():
                normalized.extend(["--port", token[2:]])
            else:
                normalized.append(token)
        return normalized
    return raw


def main(argv: list[str] | None = None) -> None:
    parser = _make_parser()
    args = parser.parse_args(_normalize_argv(argv))
    try:
        args.func(args)
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(f"agilang: error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
