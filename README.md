# AGILANG

**AGILANG** is a lightweight programming language and application framework built for developers who want a simpler, faster, and more flexible way to create modern applications.

AGILANG is designed for building:

* Backend applications
* Reactive web apps using `.ags` templates
* APIs and JSON services
* Blog and news platforms
* Social media apps
* Short-video apps
* Dashboard systems
* Web3 and blockchain applications
* Real-time apps
* Shared-hosting deployable applications
* Business and SaaS platforms

AGILANG focuses on clean syntax, fast project setup, editable app structure, reactive templates, live API data, and portable deployment.

---

## Project Information

**Language name:** AGILANG
**Template engine:** AGS Reactive Templates
**Default template extension:** `.ags`
**Source file extension:** `.agi`
**License:** MIT
**Developed by:** Izukanji Sirwimba, AGILab, Izurex Center Place Limited

---

## Table of Contents

1. [What is AGILANG?](#what-is-agilang)
2. [Installation](#installation)
3. [Creating Your First App](#creating-your-first-app)
4. [Project Structure](#project-structure)
5. [Basic Syntax](#basic-syntax)
6. [Variables and Constants](#variables-and-constants)
7. [Functions](#functions)
8. [Conditionals](#conditionals)
9. [Loops](#loops)
10. [Web App Basics](#web-app-basics)
11. [Routes](#routes)
12. [JSON APIs](#json-apis)
13. [AGS Reactive Templates](#ags-reactive-templates)
14. [Live Data Binding](#live-data-binding)
15. [Database Usage](#database-usage)
16. [Authentication Example](#authentication-example)
17. [Splitting Code into Multiple Files](#splitting-code-into-multiple-files)
18. [Creating Pages](#creating-pages)
19. [Creating APIs](#creating-apis)
20. [Stripe API Example](#stripe-api-example)
21. [PayPal API Example](#paypal-api-example)
22. [Error Handling](#error-handling)
23. [Debugging Invalid JSON Errors](#debugging-invalid-json-errors)
24. [Testing](#testing)
25. [Deployment](#deployment)
26. [Roadmap](#roadmap)
27. [Contributing](#contributing)
28. [License](#license)

---

# What is AGILANG?

AGILANG is a programming language and web application framework designed to make application development easier.

The goal of AGILANG is to allow a developer to move quickly from an idea to a working application.

AGILANG supports backend routes, API responses, reactive templates, database logic, app structure, and starter kits.

Example:

```agi
fn health(request):
    return json_response({
        "ok": true,
        "runtime": "agilang"
    })

app.get("/health", health)
```

When visited in the browser or API client:

```text
GET /health
```

Response:

```json
{
  "ok": true,
  "runtime": "agilang"
}
```

---

# Installation

AGILANG can be installed as a local development tool.

```bash
pip install -e ./docs
```

Check version:

```bash
agilang --version
```

or:

```bash
agi --version
```

Expected output:

```text
AGILANG 2.x.x
```

---

# Creating Your First App

Create a new AGILANG application:

```bash
agilang new myapp
```

or:

```bash
agi new myapp
```

Enter the project:

```bash
cd myapp
```

Run the app:

```bash
agilang serve src/main.agi --host 127.0.0.1 --port 8000
```

or:

```bash
agi serve src/main.agi --8000
```

Open:

```text
http://127.0.0.1:8000
```

---

# Project Structure

A professional AGILANG project should be structured like this:

```text
myapp/
├─ src/
│  ├─ main.agi
│  ├─ config.agi
│  ├─ routes/
│  │  ├─ web.agi
│  │  ├─ api.agi
│  │  ├─ auth.agi
│  │  ├─ profile.agi
│  │  ├─ admin.agi
│  │  └─ payments.agi
│  ├─ controllers/
│  │  ├─ HomeController.agi
│  │  ├─ ProfileController.agi
│  │  ├─ BlogController.agi
│  │  ├─ SocialController.agi
│  │  └─ PaymentController.agi
│  ├─ services/
│  │  ├─ StripeService.agi
│  │  ├─ PayPalService.agi
│  │  └─ MailService.agi
│  ├─ models/
│  │  ├─ User.agi
│  │  ├─ Post.agi
│  │  └─ Transaction.agi
│  └─ middleware/
│     ├─ csrf.agi
│     ├─ auth.agi
│     └─ errors.agi
├─ resources/
│  ├─ views/
│  │  ├─ layout.ags
│  │  ├─ home.ags
│  │  ├─ dashboard.ags
│  │  ├─ profile.ags
│  │  ├─ admin.ags
│  │  └─ payments.ags
│  └─ assets/
│     ├─ css/
│     │  └─ app.css
│     └─ js/
│        └─ ags-runtime.js
├─ storage/
│  ├─ uploads/
│  ├─ logs/
│  └─ .gitkeep
├─ tests/
│  └─ test_main.agi
├─ vendor/
│  └─ agilang/
├─ public_html/
│  ├─ app.cgi
│  └─ app.fcgi
├─ passenger_wsgi.py
├─ .env.example
├─ .gitignore
└─ README.md
```

This structure keeps the application clean. Instead of writing everything inside `src/main.agi`, you can split your code into routes, controllers, services, models, middleware, and templates.

---

# Basic Syntax

AGILANG uses readable function-based syntax.

```agi
fn main() -> i32:
    print("Hello from AGILANG")
    return 0
```

Run:

```bash
agilang run src/main.agi
```

---

# Variables and Constants

Use `let` for variables:

```agi
let name = "AGILANG"
let version = "2.0"
let active = true
```

Use `const` for constants:

```agi
const APP_NAME = "My AGILANG App"
const APP_ENV = "development"
```

---

# Environment Variables

Use environment variables for secrets and configuration.

```agi
const APP_SECRET = env("APP_SECRET", "change-this-secret")
const APP_URL = env("APP_URL", "http://127.0.0.1:8000")
const DB_PATH = env("DATABASE_PATH", "storage/app.sqlite")
```

Example `.env.example`:

```env
APP_NAME=My AGILANG App
APP_ENV=local
APP_URL=http://127.0.0.1:8000
APP_SECRET=replace-with-a-long-random-secret
DATABASE_PATH=storage/app.sqlite
STRIPE_SECRET_KEY=
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=
```

Never hardcode private API keys directly inside source files.

---

# Functions

Define a function:

```agi
fn greet(name):
    return "Hello, " + name
```

Use the function:

```agi
let message = greet("Developer")
print(message)
```

Function with return type:

```agi
fn add(a, b) -> i32:
    return a + b
```

---

# Conditionals

```agi
let age = 20

if age >= 18:
    print("Adult")
else:
    print("Minor")
```

Multiple conditions:

```agi
if role == "admin":
    print("Admin dashboard")
elif role == "editor":
    print("Editor dashboard")
else:
    print("User dashboard")
```

---

# Loops

Loop over a list:

```agi
let names = ["Amina", "John", "Mary"]

for name in names:
    print(name)
```

Loop over posts:

```agi
for post in posts:
    print(post["title"])
```

---

# Web App Basics

Create a web application:

```agi
fn create_app():
    let app = web_app("myapp", true)

    fn home(request):
        return html_response("<h1>Welcome to AGILANG</h1>")

    app.get("/", home)

    return app
```

Run the app:

```agi
fn main() -> i32:
    let app = create_app()
    let server = app.listen("127.0.0.1", 8000)
    print("Running at " + server.url)
    server.run()
    return 0
```

---

# Routes

Routes connect URLs to functions.

```agi
app.get("/", home)
app.get("/about", about)
app.get("/dashboard", dashboard)
app.post("/contact", submit_contact)
```

Example:

```agi
fn about(request):
    return html_response("<h1>About this app</h1>")

app.get("/about", about)
```

---

# JSON APIs

Use `json_response()` to return API data.

```agi
fn api_status(request):
    return json_response({
        "ok": true,
        "service": "myapp",
        "status": "online"
    })

app.get("/api/status", api_status)
```

Response:

```json
{
  "ok": true,
  "service": "myapp",
  "status": "online"
}
```

---

# API With Input

```agi
fn create_post(request):
    let title = request.input("title", "")
    let body = request.input("body", "")

    if title == "":
        return json_response({
            "ok": false,
            "error": "title_required"
        }, status=422)

    return json_response({
        "ok": true,
        "message": "Post created",
        "post": {
            "title": title,
            "body": body
        }
    })

app.post("/api/posts", create_post)
```

---

# AGS Reactive Templates

AGILANG uses `.ags` files for reactive templates.

Example:

```text
resources/views/home.ags
```

```ags
@page title="Home"
@layout "layout.ags"

<section class="hero">
    <h1>Welcome to AGILANG</h1>
    <p>Build backend apps, APIs, dashboards, and reactive web apps.</p>
</section>
```

Render the template from AGILANG:

```agi
fn home(request):
    return render_ags("home.ags", {
        "app_name": "AGILANG"
    })
```

---

# Layout Templates

A layout wraps all pages.

```text
resources/views/layout.ags
```

```ags
<!doctype html>
<html>
<head>
    <title>{{ title }}</title>
    <link rel="stylesheet" href="/assets/css/app.css">
</head>
<body>
    <header>
        <a href="/">Home</a>
        <a href="/dashboard">Dashboard</a>
    </header>

    <main>
        {{{ body }}}
    </main>

    <script src="/assets/js/ags-runtime.js"></script>
</body>
</html>
```

The `{{{ body }}}` section is where each page content is inserted.

---

# Live Data Binding

AGS templates can fetch live data from backend APIs.

```ags
@page title="Dashboard"
@layout "layout.ags"

@fetch stats from "/api/home-stats"
@live stats from "/api/home-stats" every 5000

<section>
    <h1>Dashboard</h1>
    <p>Total users: {{ stats.users }}</p>
    <p>Total posts: {{ stats.posts }}</p>
    <p>Status: {{ stats.status }}</p>
</section>
```

Backend API:

```agi
fn api_home_stats(request):
    return json_response({
        "users": 12,
        "posts": 48,
        "status": "online"
    })

app.get("/api/home-stats", api_home_stats)
```

The browser updates `stats.users`, `stats.posts`, and `stats.status` without refreshing the full page.

---

# Database Usage

Open a SQLite database:

```agi
const DB_PATH = env("DATABASE_PATH", "storage/app.sqlite")

fn db():
    ensure_dir("storage")
    return sqlite_db(DB_PATH)
```

Create a table:

```agi
fn migrate_app(app_db):
    app_db.execute("
        create table if not exists users (
            id integer primary key autoincrement,
            name text not null,
            email text not null unique,
            password_hash text not null,
            created_at text not null default current_timestamp
        )
    ")
```

Insert data:

```agi
app_db.execute(
    "insert into users (name, email, password_hash) values (?, ?, ?)",
    [name, email, hash_password(password)]
)
```

Read data:

```agi
let user = app_db.one(
    "select id, name, email from users where email = ?",
    [email]
)
```

Read many rows:

```agi
let posts = app_db.all(
    "select * from posts order by id desc",
    []
)
```

---

# Authentication Example

Register user:

```agi
fn register_action(request):
    let name = request.input("name", "").strip()
    let email = request.input("email", "").strip().lower()
    let password = request.input("password", "")

    if name == "" or email == "" or password == "":
        return json_response({
            "ok": false,
            "error": "missing_required_fields"
        }, status=422)

    let app_db = db()

    try:
        app_db.execute(
            "insert into users (name, email, password_hash) values (?, ?, ?)",
            [name, email, hash_password(password)]
        )
    except Exception:
        return json_response({
            "ok": false,
            "error": "account_exists"
        }, status=422)

    return json_response({
        "ok": true,
        "message": "Account created"
    })
```

Login user:

```agi
fn login_action(request):
    let email = request.input("email", "").strip().lower()
    let password = request.input("password", "")

    let app_db = db()
    let user = app_db.one(
        "select * from users where email = ?",
        [email]
    )

    if user == None or not verify_password(password, user["password_hash"]):
        return json_response({
            "ok": false,
            "error": "invalid_login"
        }, status=401)

    return login_user(
        json_response({
            "ok": true,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"]
            }
        }),
        {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        },
        APP_SECRET,
        cookie_name="agilang_session",
        max_age=86400
    )
```

---

# Splitting Code into Multiple Files

As applications grow, do not place everything inside `src/main.agi`.

Use a split-file structure.

Recommended:

```text
src/
├─ main.agi
├─ config.agi
├─ routes/
│  ├─ web.agi
│  ├─ api.agi
│  ├─ profile.agi
│  └─ admin.agi
├─ controllers/
│  ├─ HomeController.agi
│  ├─ ProfileController.agi
│  └─ AdminController.agi
└─ services/
   ├─ StripeService.agi
   └─ PayPalService.agi
```

## Main App File

```text
src/main.agi
```

```agi
include "config.agi"
include "routes/web.agi"
include "routes/api.agi"
include "routes/profile.agi"
include "routes/admin.agi"

fn create_app():
    let app = web_app(APP_NAME, true)

    register_web_routes(app)
    register_api_routes(app)
    register_profile_routes(app)
    register_admin_routes(app)

    return app

fn main() -> i32:
    let app = create_app()
    let server = app.listen("127.0.0.1", 8000)
    print("Running at " + server.url)
    server.run()
    return 0
```

## Config File

```text
src/config.agi
```

```agi
const APP_NAME = env("APP_NAME", "AGILANG App")
const APP_URL = env("APP_URL", "http://127.0.0.1:8000")
const APP_SECRET = env("APP_SECRET", "change-this-secret")
const DATABASE_PATH = env("DATABASE_PATH", "storage/app.sqlite")
```

## Web Routes File

```text
src/routes/web.agi
```

```agi
include "../controllers/HomeController.agi"

fn register_web_routes(app):
    app.get("/", home_page)
    app.get("/about", about_page)
    app.get("/dashboard", dashboard_page)
```

## Home Controller

```text
src/controllers/HomeController.agi
```

```agi
fn home_page(request):
    return render_ags("home.ags", {
        "title": "Home"
    })

fn about_page(request):
    return render_ags("about.ags", {
        "title": "About"
    })

fn dashboard_page(request):
    return render_ags("dashboard.ags", {
        "title": "Dashboard"
    })
```

This keeps your project organized.

Instead of writing 3,000 lines inside `main.agi`, each feature has its own file.

---

# Creating Pages

Create a new page:

```bash
agilang make:page profile
```

Expected file:

```text
resources/views/profile.ags
```

Example:

```ags
@page title="Profile"
@layout "layout.ags"

<section class="page">
    <h1>My Profile</h1>
    <p>Name: {{ user.name }}</p>
    <p>Email: {{ user.email }}</p>
</section>
```

Add route:

```agi
fn profile_page(request):
    let user = current_user(request)

    if user == None:
        return redirect("/login")

    return render_ags("profile.ags", {
        "user": user
    })

app.get("/profile", profile_page)
```

---

# Creating APIs

Create an API route file:

```text
src/routes/api.agi
```

```agi
include "../controllers/ApiController.agi"

fn register_api_routes(app):
    app.get("/api/status", api_status)
    app.get("/api/profile", api_profile)
    app.post("/api/posts", api_create_post)
```

Create the controller:

```text
src/controllers/ApiController.agi
```

```agi
fn api_status(request):
    return json_response({
        "ok": true,
        "status": "online"
    })

fn api_profile(request):
    let user = current_user(request)

    if user == None:
        return json_response({
            "ok": false,
            "error": "authentication_required"
        }, status=401)

    return json_response({
        "ok": true,
        "user": user
    })
```

---

# Stripe API Example

This example shows how an AGILANG backend can prepare a Stripe-style payment request.

Do not hardcode secret keys. Use environment variables.

```env
STRIPE_SECRET_KEY=sk_test_xxxxxxxxx
STRIPE_API_URL=https://api.stripe.com/v1
```

Service file:

```text
src/services/StripeService.agi
```

```agi
const STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", "")
const STRIPE_API_URL = env("STRIPE_API_URL", "https://api.stripe.com/v1")

fn stripe_headers():
    return {
        "Authorization": "Bearer " + STRIPE_SECRET_KEY,
        "Content-Type": "application/x-www-form-urlencoded"
    }

fn create_stripe_checkout_session(amount, currency, success_url, cancel_url):
    if STRIPE_SECRET_KEY == "":
        return {
            "ok": false,
            "error": "stripe_secret_missing"
        }

    let payload = {
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "line_items[0][price_data][currency]": currency,
        "line_items[0][price_data][product_data][name]": "AGILANG Order",
        "line_items[0][price_data][unit_amount]": amount,
        "line_items[0][quantity]": 1
    }

    try:
        let response = http_post(
            STRIPE_API_URL + "/checkout/sessions",
            payload,
            headers=stripe_headers()
        )

        return {
            "ok": true,
            "response": response
        }
    except Exception as error:
        return {
            "ok": false,
            "error": "stripe_request_failed",
            "message": str(error)
        }
```

Route usage:

```agi
include "../services/StripeService.agi"

fn api_create_payment(request):
    let amount = 5000
    let currency = "usd"

    let result = create_stripe_checkout_session(
        amount,
        currency,
        APP_URL + "/payment/success",
        APP_URL + "/payment/cancel"
    )

    if not result["ok"]:
        return json_response(result, status=500)

    return json_response(result)

app.post("/api/payments/stripe", api_create_payment)
```

---

# PayPal API Example

Example `.env`:

```env
PAYPAL_CLIENT_ID=your-client-id
PAYPAL_CLIENT_SECRET=your-client-secret
PAYPAL_API_URL=https://api-m.sandbox.paypal.com
```

Service file:

```text
src/services/PayPalService.agi
```

```agi
const PAYPAL_CLIENT_ID = env("PAYPAL_CLIENT_ID", "")
const PAYPAL_CLIENT_SECRET = env("PAYPAL_CLIENT_SECRET", "")
const PAYPAL_API_URL = env("PAYPAL_API_URL", "https://api-m.sandbox.paypal.com")

fn paypal_auth_header():
    return basic_auth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)

fn get_paypal_access_token():
    if PAYPAL_CLIENT_ID == "" or PAYPAL_CLIENT_SECRET == "":
        return {
            "ok": false,
            "error": "paypal_credentials_missing"
        }

    try:
        let response = http_post(
            PAYPAL_API_URL + "/v1/oauth2/token",
            {
                "grant_type": "client_credentials"
            },
            headers={
                "Authorization": paypal_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )

        return {
            "ok": true,
            "access_token": response["access_token"]
        }
    except Exception as error:
        return {
            "ok": false,
            "error": "paypal_token_request_failed",
            "message": str(error)
        }

fn create_paypal_order(amount, currency):
    let token_result = get_paypal_access_token()

    if not token_result["ok"]:
        return token_result

    try:
        let response = http_post_json(
            PAYPAL_API_URL + "/v2/checkout/orders",
            {
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "amount": {
                            "currency_code": currency,
                            "value": amount
                        }
                    }
                ]
            },
            headers={
                "Authorization": "Bearer " + token_result["access_token"],
                "Content-Type": "application/json"
            }
        )

        return {
            "ok": true,
            "order": response
        }
    except Exception as error:
        return {
            "ok": false,
            "error": "paypal_order_failed",
            "message": str(error)
        }
```

Route usage:

```agi
include "../services/PayPalService.agi"

fn api_create_paypal_order(request):
    let result = create_paypal_order("25.00", "USD")

    if not result["ok"]:
        return json_response(result, status=500)

    return json_response(result)

app.post("/api/payments/paypal", api_create_paypal_order)
```

---

# Error Handling

Use `try` and `except` to prevent app crashes.

```agi
fn safe_action(request):
    try:
        let result = dangerous_operation()

        return json_response({
            "ok": true,
            "result": result
        })
    except Exception as error:
        return json_response({
            "ok": false,
            "error": "operation_failed",
            "message": str(error)
        }, status=500)
```

For page routes, return a proper error page:

```agi
fn safe_page(request):
    try:
        return render_ags("dashboard.ags", {
            "title": "Dashboard"
        })
    except Exception as error:
        log_error("dashboard_failed", error)

        return render_ags("errors/500.ags", {
            "title": "Server Error",
            "message": "The dashboard could not be loaded."
        }, status=500)
```

---

# Debugging Invalid JSON Errors

Sometimes a page may fail and return an invalid JSON error.

Common causes:

1. The route returned a Python/AGILANG object instead of HTML.
2. The template renderer returned metadata and body together.
3. The API returned text that is not valid JSON.
4. A variable in `.ags` is missing.
5. A live API returns HTML instead of JSON.
6. The page is using `json_response()` where `html_response()` or `render_ags()` should be used.

## Bad Example

```agi
fn social_page(request):
    let view = render_ags_view("social.ags", {})
    return html_response(view)
```

This can print:

```text
{'body': '...', 'meta': {...}}
```

## Correct Example

```agi
fn social_page(request):
    let view = render_ags_view("social.ags", {})
    return html_response(view["body"])
```

## Better Helper Function

Create a helper to avoid this bug:

```agi
fn page_response(template, data):
    try:
        let view = render_ags_view(template, data)

        if type(view) == "dict" and "body" in view:
            return html_response(view["body"])

        return html_response(view)
    except Exception as error:
        log_error("page_render_failed", error)

        return html_response(
            "<h1>Page Error</h1><p>This page could not be rendered.</p>",
            status=500
        )
```

Now use:

```agi
fn social_page(request):
    return page_response("social.ags", {
        "title": "Social"
    })
```

## Debug API JSON

For APIs, always return valid JSON:

```agi
fn api_example(request):
    try:
        return json_response({
            "ok": true,
            "data": {
                "message": "API works"
            }
        })
    except Exception as error:
        return json_response({
            "ok": false,
            "error": "api_failed",
            "message": str(error)
        }, status=500)
```

---

# Logging Errors

Create a logging helper:

```agi
fn log_error(code, error):
    ensure_dir("storage/logs")

    let line = now() + " [" + code + "] " + str(error) + "\n"

    append_file("storage/logs/app.log", line)
```

Use it:

```agi
try:
    run_task()
except Exception as error:
    log_error("task_failed", error)
```

Check logs:

```text
storage/logs/app.log
```

---

# Debug Mode

Use an environment variable:

```env
APP_DEBUG=true
```

Config:

```agi
const APP_DEBUG = env("APP_DEBUG", "false")
```

Error response:

```agi
fn error_response(message, error, status=500):
    if APP_DEBUG == "true":
        return json_response({
            "ok": false,
            "message": message,
            "debug": str(error)
        }, status=status)

    return json_response({
        "ok": false,
        "message": message
    }, status=status)
```

---

# CSRF Protection

For form requests:

```agi
fn valid_csrf(request):
    let token = request.input("_csrf", "")

    if token == "":
        return false

    return verify_cookie(token, APP_SECRET) != None
```

Use it:

```agi
fn update_profile(request):
    if not valid_csrf(request):
        return json_response({
            "ok": false,
            "error": "csrf_failed"
        }, status=403)

    return json_response({
        "ok": true
    })
```

For API requests:

```agi
fn valid_api_csrf(request):
    let token = request.header("X-CSRF-Token", "")

    if token == "":
        return false

    return verify_cookie(token, APP_SECRET) != None
```

---

# Uploading Files

Example profile image upload:

```agi
fn upload_avatar(request):
    let user = current_user(request)

    if user == None:
        return json_response({
            "ok": false,
            "error": "authentication_required"
        }, status=401)

    let file = request.file("avatar")

    if file == None:
        return json_response({
            "ok": false,
            "error": "file_required"
        }, status=422)

    ensure_dir("storage/uploads/avatars")

    let path = "storage/uploads/avatars/" + str(user["id"]) + "-" + file.name
    file.save(path)

    return json_response({
        "ok": true,
        "avatar": path
    })
```

---

# Social Media Example

Create a social post:

```agi
fn create_social_post(request):
    let user = current_user(request)

    if user == None:
        return json_response({
            "ok": false,
            "error": "authentication_required"
        }, status=401)

    let body = request.input("body", "")

    if body == "":
        return json_response({
            "ok": false,
            "error": "post_body_required"
        }, status=422)

    let app_db = db()

    app_db.execute(
        "insert into social_posts (user_id, body) values (?, ?)",
        [user["id"], body]
    )

    return json_response({
        "ok": true,
        "message": "Post created"
    })
```

Get social feed:

```agi
fn api_social_feed(request):
    let app_db = db()

    let posts = app_db.all(
        "select social_posts.*, users.name from social_posts join users on users.id = social_posts.user_id order by social_posts.id desc",
        []
    )

    return json_response({
        "ok": true,
        "items": posts
    })
```

---

# Video Feed Example

```agi
fn upload_video(request):
    let user = current_user(request)

    if user == None:
        return json_response({
            "ok": false,
            "error": "authentication_required"
        }, status=401)

    let video = request.file("video")

    if video == None:
        return json_response({
            "ok": false,
            "error": "video_required"
        }, status=422)

    ensure_dir("storage/uploads/videos")

    let path = "storage/uploads/videos/" + str(user["id"]) + "-" + video.name
    video.save(path)

    let app_db = db()

    app_db.execute(
        "insert into short_videos (user_id, video_path) values (?, ?)",
        [user["id"], path]
    )

    return json_response({
        "ok": true,
        "video": path
    })
```

---

# Dating Discovery Example

For dating or discovery apps, always include safety rules, age checks, moderation, blocking, and reporting.

```agi
fn update_dating_profile(request):
    let user = current_user(request)

    if user == None:
        return json_response({
            "ok": false,
            "error": "authentication_required"
        }, status=401)

    let age = int(request.input("age", "0"))

    if age < 18:
        return json_response({
            "ok": false,
            "error": "adult_only"
        }, status=403)

    let about = request.input("about", "")
    let location = request.input("location", "")

    let app_db = db()

    app_db.execute(
        "update dating_profiles set age = ?, about = ?, location = ? where user_id = ?",
        [age, about, location, user["id"]]
    )

    return json_response({
        "ok": true,
        "message": "Profile updated"
    })
```

---

# Testing

Run all tests:

```bash
agilang test
```

Run a specific file:

```bash
agilang run tests/test_main.agi
```

Example test:

```agi
fn test_health():
    let app = create_app()
    let response = test_get(app, "/health")

    assert response.status == 200
    assert response.json["ok"] == true
```

---

# Checking Code

Run static checks:

```bash
agilang check src tests
```

Format code:

```bash
agilang fmt src
```

---

# Deployment

AGILANG apps can be deployed in several ways.

## Local Development

```bash
agilang serve src/main.agi --host 127.0.0.1 --port 8000
```

## VPS Deployment

```bash
agilang serve src/main.agi --host 0.0.0.0 --port 8000
```

Use Nginx or Caddy as reverse proxy.

## cPanel / Shared Hosting

The project may include:

```text
public_html/app.cgi
public_html/app.fcgi
passenger_wsgi.py
vendor/agilang/
```

The local `vendor/agilang` runtime allows the app to ship with the required AGILANG files.

Typical shared hosting flow:

1. Upload project files.
2. Make sure `storage/` is writable.
3. Set environment variables.
4. Point the web root to `public_html/`.
5. Visit your domain.

---

# Common CLI Commands

```bash
agilang --version
agilang new myapp
agilang run
agilang serve src/main.agi --8000
agilang check src tests
agilang test
agilang make:page profile
agilang make:api payments
agilang make:component user-card
```

---

# Roadmap

Planned AGILANG development includes:

* Stronger AGS reactive rendering
* Better automatic live data binding
* WebSocket support
* WebRTC starter modules
* Blockchain starter kits
* Package manager support
* Stripe and PayPal starter services
* Social network starter apps
* Video upload starter apps
* File upload helpers
* Better debugging tools
* Better error pages
* VS Code extension
* Syntax highlighting
* More deployment helpers

---

# Contributing

Contributions are welcome.

You can help by:

* Testing AGILANG
* Improving documentation
* Reporting bugs
* Creating starter kits
* Improving AGS templates
* Adding examples
* Building deployment guides
* Improving error handling
* Creating editor support

---

# License

AGILANG is released under the MIT License.

```text
MIT License

Copyright (c) Izukanji Sirwimba, AGILAB, Izurex Enterprise Limited

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files, to deal in the Software
without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, subject to the conditions of the MIT License.
```

---

# Final Vision

AGILANG is a programming language and application framework for building modern apps with simple syntax, backend logic, reactive `.ags` templates, APIs, live data, database support, and portable deployment.

It is built for developers, creators, businesses, students, and teams who want to build powerful applications without unnecessary complexity.
