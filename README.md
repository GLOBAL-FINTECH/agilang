# AGILANG

**AGILANG** is a lightweight programming language and application framework built for developers who want a simpler, faster, and more flexible way to create modern applications.

AGILANG is designed for backend applications, APIs, reactive `.ags` templates, dashboards, blog/news platforms, social apps, real-time apps, blockchain/Web3 experiments, and deployable business systems.

**License:** MIT  
**Developed by:** Izukanji Sirwimba, AGILab, Izurex Center Place Limited

---

## 1. Quick Start

Install AGILANG from the local project runtime:

```bash
pip install -e ./docs
```

Check the version:

```bash
agilang --version
# or
agi --version
```

Create a new app:

```bash
agilang new myapp
cd myapp
```

Run the app:

```bash
agilang serve src/main.agi --host 127.0.0.1 --port 8000
```

Shortcut form:

```bash
agi serve src/main.agi --8000
```

Open:

```text
http://127.0.0.1:8000
```

---

## 2. AGILANG File Types

| File type | Purpose |
|---|---|
| `.agi` | AGILANG source code: routes, controllers, services, backend logic |
| `.ags` | AGS reactive view templates |
| `.toml` | Project configuration |
| `.sql` | SQL migrations |
| `.py` | Optional generated/bridged Python runtime files |
| `.c` | Optional generated C backend/native runtime files |

---

## 3. Recommended Project Structure

```text
myapp/
├─ agilang.toml
├─ .env.example
├─ src/
│  ├─ main.agi
│  ├─ config.agi
│  ├─ routes/
│  │  ├─ web.agi
│  │  ├─ api.agi
│  │  └─ payments.agi
│  ├─ controllers/
│  │  ├─ HomeController.agi
│  │  ├─ ProfileController.agi
│  │  └─ PaymentController.agi
│  ├─ services/
│  │  ├─ StripeService.agi
│  │  └─ PayPalService.agi
│  └─ middleware/
│     ├─ auth.agi
│     └─ csrf.agi
├─ resources/
│  ├─ views/
│  │  ├─ layout.ags
│  │  ├─ home.ags
│  │  ├─ dashboard.ags
│  │  └─ profile.ags
│  └─ assets/
│     ├─ css/app.css
│     └─ js/ags-runtime.js
├─ database/migrations/
├─ storage/
├─ tests/
├─ vendor/agilang/
├─ public_html/
└─ passenger_wsgi.py
```

Use this structure so one large `main.agi` file can be split into smaller files.

---

## 4. Basic Syntax

### Hello World

```agi
fn main() -> i32:
    print("Hello from AGILANG")
    return 0
```

Run:

```bash
agilang run src/main.agi
```

### Comments

```agi
# This is a comment
```

### Variables and Constants

```agi
let name = "AGILANG"
let count: i32 = 10
const APP_NAME = "My App"
```

### Functions

```agi
fn greet(name: string) -> string:
    return "Hello, " + name
```

### Conditionals

```agi
if role == "admin":
    print("Admin")
elif role == "editor":
    print("Editor")
else:
    print("User")
```

### Loops

```agi
for name in ["Amina", "John", "Mary"]:
    print(name)
```

### Type Aliases

```agi
type UserId = i64
let id: UserId = 1
```

### Structs

```agi
struct User:
    id: i32
    name: string
    email: string
```

### Enums

```agi
enum PostStatus:
    DRAFT
    PUBLISHED
    ARCHIVED
```

---

## 5. Importing and Splitting Code

AGILANG supports importing other `.agi` files with `import "file.agi"`.

> Use `import`, not `include`.

Example `src/main.agi`:

```agi
import "config.agi"
import "routes/web.agi"
import "routes/api.agi"

fn create_app():
    let app = web_app(APP_NAME, True)
    register_web_routes(app)
    register_api_routes(app)
    return app
```

Example `src/config.agi`:

```agi
import os

const APP_NAME = os.environ.get("APP_NAME", "AGILANG App")
const APP_URL = os.environ.get("APP_URL", "http://127.0.0.1:8000").rstrip("/")
const APP_SECRET = os.environ.get("APP_SECRET", "change-me")
```

Example `src/routes/web.agi`:

```agi
import "../controllers/HomeController.agi"

fn register_web_routes(app):
    app.get("/", home_page)
    app.get("/dashboard", dashboard_page)
```

Example `src/controllers/HomeController.agi`:

```agi
fn home_page(request):
    let view = render_ags("../resources/views/home.ags", {"title": "Home"})
    return html_response(render_template("../resources/views/layout.ags", {
        "title": view["meta"].get("title", "Home"),
        "seo": view["seo"],
        "body": view["body"]
    }))
```

This is the correct pattern for building large AGILANG applications.

---

## 6. Web App Basics

Create a web app:

```agi
fn create_app():
    let app = web_app("myapp", True)

    fn home(request):
        return html_response("<h1>Welcome</h1>")

    app.get("/", home)
    return app
```

Serve:

```bash
agilang serve src/main.agi --host 127.0.0.1 --port 8000
```

Supported routes:

```agi
app.get("/path", handler)
app.post("/path", handler)
app.put("/path", handler)
app.delete("/path", handler)
app.any("/path", handler)
```

Route parameters:

```agi
fn show_post(request):
    let id = request.input("id", "")
    return json_response({"post_id": id})

app.get("/posts/<id>", show_post)
```

---

## 7. Request Input

```agi
let id = request.input("id", "")
let email = request.input("email", "")
let body = request.json(default={})
let query = request.query
let cookies = request.cookies
```

---

## 8. Responses

```agi
return html_response("<h1>Hello</h1>")
return text_response("Plain text")
return json_response({"ok": True})
return redirect("/dashboard")
return file_response("storage/report.pdf", download_name="report.pdf")
```

---

## 9. AGS Reactive Templates

`resources/views/home.ags`:

```ags
@page title="Home" seo_description="AGILANG reactive home page."
@layout "layout.ags"
@fetch stats from "/api/home-stats"
@live stats from "/api/home-stats" every 5000

<section class="hero">
  <h1>Welcome to {{ app_name }}</h1>
  <p>Total users: {{ stats.users }}</p>
  <p>Total posts: {{ stats.posts }}</p>
  <p>Status: {{ stats.status }}</p>
</section>
```

Backend route:

```agi
fn api_home_stats(request):
    return json_response({
        "users": 10,
        "posts": 25,
        "status": "online"
    })

app.get("/api/home-stats", api_home_stats)
```

The AGS renderer converts `{{ stats.users }}` into automatic browser live binding.

---

## 10. Layout Template

`resources/views/layout.ags`:

```ags
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
  <header>
    <a href="/">Home</a>
    <a href="/dashboard">Dashboard</a>
  </header>

  <main>
    {{{ body }}}
  </main>
</body>
</html>
```

---

## 11. Database

SQLite:

```agi
const DB_PATH = os.environ.get("DATABASE_PATH", "../storage/app.sqlite")

fn db():
    ensure_dir("../storage")
    return sqlite_db(DB_PATH)
```

Migration:

```agi
fn migrate_app(app_db):
    app_db.execute("create table if not exists users (id integer primary key autoincrement, name text not null, email text not null unique, password_hash text not null)")
```

Insert:

```agi
app_db.execute("insert into users (name, email, password_hash) values (?, ?, ?)", [name, email, hash_password(password)])
```

Query one:

```agi
let user = app_db.one("select * from users where email = ?", [email])
```

Query many:

```agi
let users = app_db.query("select id, name, email from users order by id desc", [])
```

MySQL helper:

```agi
let app_db = mysql_db(host="127.0.0.1", port=3306, user="root", password="", database="myapp")
```

---

## 12. Authentication

Register:

```agi
fn register_action(request):
    let name = request.input("name", "").strip()
    let email = request.input("email", "").strip().lower()
    let password = request.input("password", "")

    if name == "" or email == "" or password == "":
        return json_response({"ok": False, "error": "missing_fields"}, status=422)

    let app_db = db()
    app_db.execute("insert into users (name, email, password_hash) values (?, ?, ?)", [name, email, hash_password(password)])

    return json_response({"ok": True})
```

Login:

```agi
fn login_action(request):
    let email = request.input("email", "").strip().lower()
    let password = request.input("password", "")
    let user = db().one("select * from users where email = ?", [email])

    if user == None or not verify_password(password, user["password_hash"]):
        return json_response({"ok": False, "error": "invalid_login"}, status=401)

    return login_user(redirect("/dashboard"), {"id": user["id"], "name": user["name"], "email": user["email"]}, APP_SECRET, cookie_name="app_session")
```

Current user:

```agi
let user = current_user(request, APP_SECRET, cookie_name="app_session")
```

---

## 13. CSRF Protection

Forms:

```agi
fn valid_csrf(request):
    let token = request.input("_csrf", "")
    if token == "":
        return False
    return verify_cookie(token, APP_SECRET) != None
```

APIs:

```agi
fn valid_api_csrf(request):
    let token = request.headers.get("x-csrf-token", "")
    if token == "":
        return False
    return verify_cookie(token, APP_SECRET) != None
```

Use it:

```agi
fn update_profile(request):
    if not valid_api_csrf(request):
        return json_response({"ok": False, "error": "csrf_failed"}, status=403)
    return json_response({"ok": True})
```

---

## 14. Error Handling and Debugging

Use `try` and `except`:

```agi
fn api_safe(request):
    try:
        let result = run_task()
        return json_response({"ok": True, "result": result})
    except Exception as exc:
        return json_response({"ok": False, "error": "task_failed", "message": str(exc)}, status=500)
```

Page rendering helper to avoid invalid JSON or object printing:

```agi
fn page_response(template, data):
    try:
        let view = render_ags(template, data)
        return html_response(render_template("../resources/views/layout.ags", {
            "title": view["meta"].get("title", "AGILANG"),
            "seo": view["seo"],
            "body": view["body"]
        }))
    except Exception as exc:
        return html_response("<h1>Page Error</h1><p>" + str(exc) + "</p>", status=500)
```

Common invalid JSON/page errors:

| Problem | Fix |
|---|---|
| Page prints `{'body': ...}` | Return `view["body"]` inside layout, not the whole view object |
| API returns HTML | Use `json_response()` for APIs only |
| Page returns JSON | Use `html_response()` or `page_response()` |
| `.ags` variable empty | Check context data passed to `render_ags()` |
| Live binding not updating | Check the API returns valid JSON and the key path exists |

Debug commands:

```bash
agilang check src tests
agilang to-py src/main.agi --line-map
agilang tokens src/main.agi
agilang ast src/main.agi --pretty
agilang run src/main.agi --dump
```

---

## 15. Stripe Example

`.env`:

```env
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_PRICE_ID=price_xxxxx
APP_URL=http://127.0.0.1:8000
```

Service:

```agi
const STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")

fn stripe_checkout_url():
    if STRIPE_SECRET_KEY == "":
        return ""
    return "https://checkout.stripe.com/"

fn create_stripe_checkout(request):
    if STRIPE_SECRET_KEY == "":
        return json_response({"ok": False, "error": "stripe_not_configured"}, status=500)

    # In production, call Stripe's Checkout Session API with http_post/http_post_json
    return json_response({
        "ok": True,
        "provider": "stripe",
        "message": "Create checkout session here",
        "success_url": APP_URL + "/payments/success",
        "cancel_url": APP_URL + "/payments/cancel"
    })
```

Route:

```agi
app.post("/api/payments/stripe", create_stripe_checkout)
```

---

## 16. PayPal Example

`.env`:

```env
PAYPAL_CLIENT_ID=your-client-id
PAYPAL_CLIENT_SECRET=your-client-secret
PAYPAL_ENV=sandbox
```

Service:

```agi
fn paypal_base_url():
    if PAYPAL_ENV == "live":
        return "https://api-m.paypal.com"
    return "https://api-m.sandbox.paypal.com"

fn create_paypal_order(request):
    if PAYPAL_CLIENT_ID == "" or PAYPAL_CLIENT_SECRET == "":
        return json_response({"ok": False, "error": "paypal_not_configured"}, status=500)

    return json_response({
        "ok": True,
        "provider": "paypal",
        "message": "Create PayPal order here",
        "api_base": paypal_base_url()
    })
```

Route:

```agi
app.post("/api/payments/paypal", create_paypal_order)
```

---

## 17. Tests

Run all tests:

```bash
agilang test
```

Run one test file:

```bash
agilang run tests/test_main.agi
```

Example test:

```agi
import "../src/main.agi"

fn main() -> i32:
    let app = create_app()
    let server = app.listen("127.0.0.1", 0)
    server.run_background()
    let response = web_get(server.url + "/health")
    print(response)
    server.stop()
    return 0
```

---

## 18. Deployment

Development:

```bash
agilang serve src/main.agi --host 127.0.0.1 --port 8000
```

VPS:

```bash
agilang serve src/main.agi --host 0.0.0.0 --port 8000
```

Shared hosting helpers:

```bash
agilang hosting scaffold --root . --entry src/main.agi --target public_html --mode auto
```

Generated hosting files may include:

```text
public_html/app.cgi
public_html/app.fcgi
public_html/.htaccess
passenger_wsgi.py
vendor/agilang/
```

---

## 19. Command Reference

See `docs/CLI_REFERENCE.md` for the full command scan.

Most-used commands:

```bash
agilang --version
agilang doctor
agilang new myapp
agilang run src/main.agi
agilang serve src/main.agi --8000
agilang check src tests
agilang test
agilang make:page profile
agilang make:component stat-card
agilang make:api home-stats
agilang to-py src/main.agi --line-map
agilang hosting scaffold
agilang blockchain demo
agilang evm build-demo
agilang zk demo
```

---

## 20. License

MIT License

Copyright (c) Izukanji Sirwimba, AGILab, Izurex Center Place Limited

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files, to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, subject to the MIT License.
