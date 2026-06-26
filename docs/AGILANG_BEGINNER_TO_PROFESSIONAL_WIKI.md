# AGILANG Beginner to Professional Wiki

This wiki teaches AGILANG from beginner level to full-stack development. It covers syntax, project structure, web apps, routes, pages, authentication, database workflows, error handling, testing, blockchain, AIFlow, deployment, and professional development practices.

> Goal: a beginner should be able to read this page, create an AGILANG app, understand `.agi` code, build web pages, handle errors, add APIs, use AIFlow, understand blockchain commands, test the project, and grow into a professional AGILANG developer.

---

## Table of contents

1. What AGILANG is
2. Installing AGILANG
3. Your first AGI program
4. AGILANG project structure
5. Core syntax
6. Variables and constants
7. Functions
8. Types and return values
9. Conditions
10. Loops
11. Structs and enums
12. Imports and modules
13. Error handling basics
14. CLI commands
15. Creating a web app
16. Routes
17. Controllers
18. AGS templates
19. Layouts and pages
20. Forms
21. Authentication
22. Sessions and cookies
23. Database and models
24. APIs and JSON responses
25. Middleware and security
26. 404 errors: simulation and fixes
27. 500 errors: simulation, collection and fixes
28. Validation errors
29. Debugging checklist
30. Testing AGILANG apps
31. Building AIFlow apps
32. Using TorchCompat
33. Blockchain development
34. Full-stack project example
35. Deployment checklist
36. Professional coding standards
37. A-to-Z learning path

---

# 1. What AGILANG is

AGILANG is a programming language and application runtime for building:

- command-line programs
- web applications
- APIs
- `.ags` template websites
- AI/ML applications through AIFlow
- blockchain/runtime projects
- real-time apps
- full-stack systems

AGILANG source files use:

```text
.agi   AGILANG source code
.ags   AGILANG reactive templates
.json  configuration files
```

A normal AGILANG project can look like this:

```text
my-app/
├─ agilang.toml
├─ src/
│  └─ main.agi
├─ routes/
│  ├─ web.agi
│  └─ api.agi
├─ app/
│  └─ controllers/
├─ resources/
│  └─ views/
│     ├─ layout.ags
│     └─ home.ags
├─ config/
├─ storage/
└─ tests/
```

---

# 2. Installing AGILANG

For development from the repository:

```bash
pip install -e .
agi --help
agilang --help
```

Run tests:

```bash
python -m pytest
```

Compile-check Python modules:

```bash
python -m compileall -q agilang tests
```

Check the AIFlow production upgrade tests:

```bash
python -m pytest tests/test_aiflow_production_upgrade.py
```

---

# 3. Your first AGI program

Create a file:

```text
hello.agi
```

Write:

```agi
fn main() -> i32:
    print("Hello from AGILANG")
    return 0
```

Run:

```bash
agi run hello.agi
```

Expected output:

```text
Hello from AGILANG
```

## What this means

```agi
fn main() -> i32:
```

Defines the `main` function and says it returns an integer.

```agi
print("Hello from AGILANG")
```

Prints text to the terminal.

```agi
return 0
```

Returns a successful exit code.

---

# 4. AGILANG project structure

A professional AGILANG app should use a clear layout:

```text
my-fullstack-app/
├─ agilang.toml
├─ src/
│  ├─ main.agi
│  ├─ auth.agi
│  ├─ dashboard.agi
│  └─ services.agi
├─ routes/
│  ├─ web.agi
│  └─ api.agi
├─ app/
│  ├─ controllers/
│  │  ├─ HomeController.agi
│  │  ├─ AuthController.agi
│  │  └─ DashboardController.agi
│  └─ models/
│     └─ User.agi
├─ resources/
│  └─ views/
│     ├─ layout.ags
│     ├─ home.ags
│     ├─ login.ags
│     └─ dashboard.ags
├─ config/
│  ├─ app.json
│  ├─ database.json
│  └─ auth.json
├─ storage/
│  ├─ logs/
│  ├─ app.sqlite
│  └─ cache/
└─ tests/
```

## Folder meaning

| Folder | Purpose |
|---|---|
| `src/` | Core AGILANG logic |
| `routes/` | Web and API routes |
| `app/controllers/` | Request handlers |
| `app/models/` | Database models |
| `resources/views/` | `.ags` pages and layouts |
| `config/` | App configuration |
| `storage/` | SQLite, logs, cache, generated files |
| `tests/` | Automated tests |

---

# 5. Core syntax

AGILANG syntax is indentation-based and Python-like, but it uses explicit function declarations.

```agi
fn main() -> i32:
    let name = "AGILANG"
    print(name)
    return 0
```

## Comments

```agi
# This is a comment
```

## Strings

```agi
let title = "My AGILANG App"
```

## Numbers

```agi
let amount = 100
let rate = 0.15
```

## Booleans

```agi
let active = true
let disabled = false
```

## Lists

```agi
let users = ["Alice", "Bob", "Carol"]
```

## Dictionaries / objects

```agi
let user = {
    "name": "Alice",
    "email": "alice@example.com"
}
```

---

# 6. Variables and constants

## Mutable variable

```agi
let count = 1
count = count + 1
```

## Constant

```agi
const APP_NAME = "AGILANG CRM"
```

Use constants for configuration-like values:

```agi
const DEFAULT_PAGE_SIZE = 20
const VERSION = "1.0.0"
```

---

# 7. Functions

## Basic function

```agi
fn greet(name) -> str:
    return "Hello " + name
```

## Function with numbers

```agi
fn add(a, b) -> i32:
    return a + b
```

## Calling a function

```agi
fn main() -> i32:
    let total = add(10, 5)
    print(total)
    return 0
```

## Professional rule

Keep functions small:

```agi
fn validate_email(email) -> bool:
    return "@" in email
```

Avoid huge functions that do routing, database, validation, and rendering all together.

---

# 8. Types and return values

Common return annotations:

```agi
fn age() -> i32:
    return 20

fn price() -> f64:
    return 10.50

fn name() -> str:
    return "AGILANG"

fn enabled() -> bool:
    return true
```

Use return types to make the code easier to understand.

---

# 9. Conditions

```agi
fn check_age(age) -> str:
    if age >= 18:
        return "adult"
    else:
        return "minor"
```

Multiple conditions:

```agi
fn grade(score) -> str:
    if score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    else:
        return "D"
```

---

# 10. Loops

## For loop

```agi
fn list_users() -> i32:
    let users = ["Alice", "Bob", "Carol"]
    for user in users:
        print(user)
    return 0
```

## While loop

```agi
fn count_to_five() -> i32:
    let i = 1
    while i <= 5:
        print(i)
        i = i + 1
    return 0
```

---

# 11. Structs and enums

Use structs to group data.

```agi
struct User:
    name: str
    email: str
    active: bool
```

Use enums for fixed states.

```agi
enum UserStatus:
    ACTIVE
    BLOCKED
    PENDING
```

Professional use:

```agi
enum TransactionStatus:
    PENDING
    CONFIRMED
    FAILED
    REVERSED
```

---

# 12. Imports and modules

Split code into modules.

```text
src/
├─ main.agi
├─ math.agi
└─ users.agi
```

Example:

```agi
import "src/users.agi"
```

Use imports when your file becomes too large.

---

# 13. Error handling basics

Use `try` and `except` around risky logic.

```agi
fn parse_amount(value) -> f64:
    try:
        return float(value)
    except:
        return 0.0
```

For professional code, do not hide every error. Return useful messages.

```agi
fn safe_divide(a, b):
    if b == 0:
        return {
            "ok": false,
            "error": "division_by_zero"
        }
    return {
        "ok": true,
        "result": a / b
    }
```

---

# 14. CLI commands

Important commands:

```bash
agi run file.agi
agi check file.agi
agi typecheck file.agi
agi tokens file.agi
agi ast file.agi
agi fmt file.agi
agi test
agi repl
agi doctor
```

AI commands:

```bash
agi ai capabilities
agi ai doctor
agi ai tokenizer-train --text "hello agilang" --out models/tokenizer.json
agi ai tokenizer-encode --model models/tokenizer.json --text "hello agilang"
agi ai lm-train --input corpus.txt --out models/domain-lm.agi-model
agi ai lm-generate --model models/domain-lm.agi-model --prompt "agilang"
agi ai onnx-status
agi ai gpu-status
agi ai distributed-status
```

Blockchain commands:

```bash
agi new my-chain --template blockchain --chain-id 1900 --symbol SBQ
agi chain status --root .
agi chain rpc --root . --host 127.0.0.1 --port 8545
agi beacon status
agi beacon simulate --validators 64 --epochs 2
```

---

# 15. Creating a web app

Create a new app:

```bash
agi new my-web-app
cd my-web-app
```

A web app needs:

```text
routes/web.agi
app/controllers/HomeController.agi
resources/views/layout.ags
resources/views/home.ags
src/main.agi
```

Basic `src/main.agi`:

```agi
fn main() -> i32:
    print("Starting AGILANG web app")
    return 0
```

---

# 16. Routes

Routes map URLs to functions.

Example route file:

```agi
# routes/web.agi

fn register_routes(app):
    app.get("/", home)
    app.get("/about", about)
    app.get("/login", login_page)
    app.post("/login", login_submit)
    app.get("/dashboard", dashboard)
```

Route examples:

| URL | Method | Function |
|---|---|---|
| `/` | GET | `home` |
| `/about` | GET | `about` |
| `/login` | GET | `login_page` |
| `/login` | POST | `login_submit` |
| `/dashboard` | GET | `dashboard` |

Professional naming:

```agi
app.get("/users", users_index)
app.get("/users/create", users_create)
app.post("/users", users_store)
app.get("/users/{id}", users_show)
app.post("/users/{id}/delete", users_delete)
```

---

# 17. Controllers

Controllers keep route logic clean.

```agi
# app/controllers/HomeController.agi

fn home(request):
    return render_ags("home.ags", {
        "title": "Welcome to AGILANG"
    })

fn about(request):
    return render_ags("about.ags", {
        "title": "About"
    })
```

Good controller rules:

- validate request data
- call services/models
- return views or JSON
- do not put huge business logic in the route file

---

# 18. AGS templates

AGS files are templates for pages.

Example:

```ags
@page home
@layout layout.ags

<h1>{{ title }}</h1>
<p>Welcome to AGILANG.</p>
```

Use escaped output:

```ags
{{ user.name }}
```

Use raw/trusted output only when safe:

```ags
{{{ trusted_html }}}
```

Professional rule: never output user-submitted HTML as raw trusted HTML unless it has been sanitized.

---

# 19. Layouts and pages

`resources/views/layout.ags`:

```ags
<!doctype html>
<html>
<head>
    <title>{{ title }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
    <nav>
        <a href="/">Home</a>
        <a href="/dashboard">Dashboard</a>
        <a href="/login">Login</a>
    </nav>

    <main>
        {{ content }}
    </main>
</body>
</html>
```

`resources/views/home.ags`:

```ags
@page home
@layout layout.ags

<h1>{{ title }}</h1>
<p>This is your first AGILANG page.</p>
```

---

# 20. Forms

Login form:

```ags
@page login
@layout layout.ags

<h1>Login</h1>
<form method="POST" action="/login">
    <label>Email</label>
    <input type="email" name="email" required>

    <label>Password</label>
    <input type="password" name="password" required>

    <button type="submit">Login</button>
</form>
```

Controller:

```agi
fn login_submit(request):
    let email = request.form("email")
    let password = request.form("password")

    if email == "" or password == "":
        return render_ags("login.ags", {
            "title": "Login",
            "error": "Email and password are required"
        })

    return redirect("/dashboard")
```

---

# 21. Authentication

Basic authentication flow:

1. user visits `/login`
2. user submits email and password
3. app validates input
4. app checks database
5. app creates session
6. app redirects to dashboard

Example:

```agi
fn login_submit(request):
    let email = request.form("email")
    let password = request.form("password")

    if not validate_email(email):
        return render_ags("login.ags", {
            "title": "Login",
            "error": "Invalid email address"
        })

    let user = find_user_by_email(email)
    if user == null:
        return render_ags("login.ags", {
            "title": "Login",
            "error": "Invalid login details"
        })

    if not verify_password(password, user["password_hash"]):
        return render_ags("login.ags", {
            "title": "Login",
            "error": "Invalid login details"
        })

    request.session_set("user_id", user["id"])
    return redirect("/dashboard")
```

Protect dashboard:

```agi
fn dashboard(request):
    let user_id = request.session_get("user_id")
    if user_id == null:
        return redirect("/login")

    return render_ags("dashboard.ags", {
        "title": "Dashboard"
    })
```

---

# 22. Sessions and cookies

Use sessions for login state.

```agi
request.session_set("user_id", user["id"])
let user_id = request.session_get("user_id")
request.session_delete("user_id")
```

Use cookies for small browser values.

```agi
response.cookie("theme", "dark")
```

Professional security rules:

- use secure cookies in production
- use HTTP-only session cookies
- rotate session after login
- never store passwords in cookies
- never store private keys in browser storage

---

# 23. Database and models

Example SQLite config:

```json
{
  "database": "storage/app.sqlite"
}
```

Create a user table:

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

Model-style functions:

```agi
fn find_user_by_email(email):
    return db.first("SELECT * FROM users WHERE email = ?", [email])

fn create_user(name, email, password_hash):
    return db.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, datetime('now'))",
        [name, email, password_hash]
    )
```

Professional database rules:

- use parameterized queries
- never concatenate user input into SQL
- add indexes for frequently searched fields
- keep migrations in version control
- back up production databases

Bad:

```agi
let sql = "SELECT * FROM users WHERE email = '" + email + "'"
```

Good:

```agi
db.first("SELECT * FROM users WHERE email = ?", [email])
```

---

# 24. APIs and JSON responses

API route:

```agi
app.get("/api/health", api_health)
```

Controller:

```agi
fn api_health(request):
    return json_response({
        "ok": true,
        "service": "agilang-app"
    })
```

User API:

```agi
fn api_user(request):
    let user_id = request.session_get("user_id")
    if user_id == null:
        return json_response({
            "ok": false,
            "error": "unauthenticated"
        }, 401)

    let user = find_user_by_id(user_id)
    return json_response({
        "ok": true,
        "user": user
    })
```

---

# 25. Middleware and security

Middleware runs before or after requests.

Authentication middleware concept:

```agi
fn auth_required(request, next):
    let user_id = request.session_get("user_id")
    if user_id == null:
        return redirect("/login")
    return next(request)
```

Security middleware should include:

- CSRF protection for forms
- rate limiting for login/API routes
- security headers
- request body size limits
- input validation
- output escaping

Example validation:

```agi
fn validate_register(data):
    let errors = {}

    if data["name"] == "":
        errors["name"] = "Name is required"

    if not validate_email(data["email"]):
        errors["email"] = "Valid email is required"

    if len(data["password"]) < 8:
        errors["password"] = "Password must be at least 8 characters"

    return errors
```

---

# 26. 404 errors: simulation and fixes

A 404 means the route or page was not found.

## Simulate 404

Visit:

```text
http://127.0.0.1:8000/this-page-does-not-exist
```

Expected:

```text
404 Not Found
```

## Common causes

| Cause | Example | Fix |
|---|---|---|
| Missing route | `/about` not registered | Add `app.get("/about", about)` |
| Wrong method | POST sent to GET route | Add POST route or change form method |
| Wrong URL | `/dashbord` typo | Use `/dashboard` |
| Missing view file | `about.ags` missing | Create `resources/views/about.ags` |

## Fix missing route

Wrong:

```agi
# no /about route
app.get("/", home)
```

Correct:

```agi
app.get("/", home)
app.get("/about", about)
```

## Fix missing view

Controller:

```agi
fn about(request):
    return render_ags("about.ags", {
        "title": "About"
    })
```

Create:

```text
resources/views/about.ags
```

```ags
@page about
@layout layout.ags

<h1>{{ title }}</h1>
<p>About this AGILANG app.</p>
```

## Custom 404 page

```ags
@page errors.404
@layout layout.ags

<h1>404 - Page not found</h1>
<p>The page you requested does not exist.</p>
<a href="/">Return home</a>
```

Controller pattern:

```agi
fn not_found(request):
    return render_ags("errors/404.ags", {
        "title": "Page not found"
    }, 404)
```

---

# 27. 500 errors: simulation, collection and fixes

A 500 means the server failed while processing the request.

## Simulate 500

Create a route:

```agi
app.get("/simulate-500", simulate_500)
```

Controller:

```agi
fn simulate_500(request):
    let value = 10 / 0
    return text_response("This will not run")
```

Visit:

```text
/simulate-500
```

Expected:

```text
500 Internal Server Error
```

## Common 500 causes

| Cause | Example | Fix |
|---|---|---|
| Division by zero | `10 / 0` | Check denominator before division |
| Missing variable | `user.name` when `user` is null | Check if user exists |
| Missing database table | `SELECT * FROM users` before migration | Run migration/create table |
| Bad JSON config | broken `config/app.json` | Validate JSON syntax |
| Missing template | render unknown `.ags` | Create template or fix path |

## Fix division by zero

Wrong:

```agi
fn calculate(request):
    let total = 100 / request.form("qty")
    return text_response(total)
```

Correct:

```agi
fn calculate(request):
    let qty = int(request.form("qty"))
    if qty == 0:
        return json_response({
            "ok": false,
            "error": "qty_must_not_be_zero"
        }, 422)

    let total = 100 / qty
    return json_response({
        "ok": true,
        "total": total
    })
```

## 500 error collection/logging

Create an error logger:

```agi
fn log_error(error, request):
    let line = {
        "path": request.path,
        "method": request.method,
        "error": str(error),
        "time": now()
    }
    file_append("storage/logs/errors.jsonl", json_encode(line) + "\n")
```

Wrap controller code:

```agi
fn safe_controller(request):
    try:
        return risky_controller(request)
    except error:
        log_error(error, request)
        return render_ags("errors/500.ags", {
            "title": "Server error"
        }, 500)
```

Create `resources/views/errors/500.ags`:

```ags
@page errors.500
@layout layout.ags

<h1>500 - Server error</h1>
<p>Something went wrong. The error has been logged.</p>
<a href="/">Return home</a>
```

Professional rule: in production, do not show internal stack traces to users. Log them privately.

---

# 28. Validation errors

Validation errors are not server errors. They should normally return `422` or show form messages.

Example:

```agi
fn register_submit(request):
    let data = {
        "name": request.form("name"),
        "email": request.form("email"),
        "password": request.form("password")
    }

    let errors = validate_register(data)
    if len(errors) > 0:
        return render_ags("register.ags", {
            "title": "Register",
            "errors": errors,
            "old": data
        }, 422)

    create_user(data["name"], data["email"], hash_password(data["password"]))
    return redirect("/login")
```

---

# 29. Debugging checklist

When something fails, check in this order:

1. Did the command run?
2. Is the file path correct?
3. Is the route registered?
4. Is the HTTP method correct?
5. Does the controller function exist?
6. Does the `.ags` template exist?
7. Is JSON config valid?
8. Did database migrations run?
9. Are required environment variables set?
10. Are permissions correct for `storage/`?
11. Is the error in logs?
12. Is the test failing in the same place?

Useful commands:

```bash
agi check src/main.agi
agi typecheck src/main.agi
python -m compileall -q agilang tests
python -m pytest -q
```

---

# 30. Testing AGILANG apps

Write tests for:

- syntax
- routes
- controllers
- validation
- database functions
- authentication
- error pages
- AI functions
- blockchain config

Example test idea:

```text
When user visits /unknown, app returns 404.
When user submits empty login form, app returns validation error.
When user visits /dashboard without login, app redirects to /login.
```

Professional rule: every bug you fix should get a test.

---

# 31. Building AIFlow apps

AIFlow includes:

```text
AGIRecord datasets
image preprocessing
CNN training
BPE tokenizer
small language model bundle
transformer runtime
ONNX bridge
TorchCompat
GPU status gate
distributed runtime coordinator
```

Check AI capabilities:

```bash
agi ai capabilities
agi ai doctor
```

Train tokenizer:

```bash
agi ai tokenizer-train --text "agilang builds ai" --out models/tokenizer.json
```

Encode text:

```bash
agi ai tokenizer-encode --model models/tokenizer.json --text "agilang builds ai"
```

Train language model:

```bash
agi ai lm-train --input corpus.txt --out models/domain-lm.agi-model --order 3
```

Generate text:

```bash
agi ai lm-generate --model models/domain-lm.agi-model --prompt "agilang" --steps 32
```

Preprocess image:

```bash
agi ai preprocess-image --input document.png --out storage/document.json --rows 224 --cols 224 --mode L
```

---

# 32. Using TorchCompat

TorchCompat gives AGILANG a PyTorch-style API surface.

```python
from agilang.torch_compat import tensor, nn, optim, mse_loss

x = tensor([[1.0, 2.0]])
y_true = tensor([[1.0]])

model = nn.Sequential(
    nn.Linear(2, 4),
    nn.ReLU(),
    nn.Linear(4, 1),
)

y_pred = model(x)
loss = mse_loss(y_pred, y_true)
loss.backward()

optimizer = optim.SGD(model.parameters(), lr=0.01)
optimizer.step()
```

Check status:

```python
from agilang.torch_compat import torch_compat_status
print(torch_compat_status())
```

Important boundary:

```text
TorchCompat is a native AGILANG PyTorch-style subset.
It is not full PyTorch operator/compiler/CUDA parity yet.
```

---

# 33. Blockchain development

Create a blockchain app:

```bash
agi new my-chain --template blockchain --chain-id 1900 --symbol SBQ --force
cd my-chain
```

Check status:

```bash
agi chain status --root .
```

Start RPC:

```bash
agi chain rpc --root . --host 127.0.0.1 --port 8545
```

Check beacon:

```bash
agi beacon status
agi beacon simulate --validators 64 --epochs 2
```

Ethereum consensus profile:

```bash
agi chain ethereum-consensus-capabilities
agi chain ethereum-consensus-write-config --chain-id 901900
agi chain ethereum-consensus-check
agi chain ethereum-consensus-sim --slots 8
```

Professional blockchain rules:

- chain ID must be unique
- never use dev keys in production
- validate transactions before execution
- reject negative balances
- reject invalid nonces
- log failed transactions
- test reorg behavior
- protect RPC endpoints
- do not expose private validator APIs publicly

---

# 34. Full-stack project example

Build a simple AGILANG dashboard app:

```text
Features:
- home page
- register/login
- dashboard
- API health endpoint
- AI capability endpoint
- custom 404 page
- custom 500 page
```

Routes:

```agi
fn register_routes(app):
    app.get("/", home)
    app.get("/login", login_page)
    app.post("/login", login_submit)
    app.get("/dashboard", dashboard)
    app.get("/api/health", api_health)
    app.get("/api/ai/capabilities", api_ai_capabilities)
    app.get("/simulate-500", simulate_500)
```

Controllers:

```agi
fn home(request):
    return render_ags("home.ags", {"title": "Home"})

fn dashboard(request):
    let user_id = request.session_get("user_id")
    if user_id == null:
        return redirect("/login")
    return render_ags("dashboard.ags", {"title": "Dashboard"})

fn api_health(request):
    return json_response({"ok": true})

fn api_ai_capabilities(request):
    return json_response(ai_capabilities())
```

---

# 35. Deployment checklist

Before deployment:

```text
[ ] Run full tests
[ ] Check syntax
[ ] Check config JSON
[ ] Set production environment variables
[ ] Secure cookies
[ ] Enable CSRF protection
[ ] Enable rate limiting
[ ] Protect admin routes
[ ] Protect RPC routes
[ ] Ensure storage/ is writable
[ ] Ensure logs are private
[ ] Remove demo credentials
[ ] Backup database
[ ] Add monitoring
[ ] Add 404 and 500 pages
[ ] Run AI deployment gate if using AI
[ ] Run blockchain consensus check if using blockchain
```

Commands:

```bash
python -m pytest
python -m compileall -q agilang tests
agi ai doctor
agi chain ethereum-consensus-check
```

---

# 36. Professional coding standards

## Naming

Good:

```agi
fn create_user_account(data):
```

Bad:

```agi
fn doStuff(x):
```

## Keep files focused

Good:

```text
AuthController.agi
UserController.agi
DashboardController.agi
```

Bad:

```text
everything.agi
```

## Validate all input

Never trust:

- form input
- query string
- JSON body
- uploaded files
- cookies
- external API responses

## Log safely

Log:

```text
error type
route
timestamp
request id
```

Do not log:

```text
passwords
private keys
card numbers
secret tokens
```

---

# 37. A-to-Z learning path

## Phase A: Beginner

Learn:

```text
print
variables
functions
conditions
loops
lists
dictionaries
```

Build:

```text
calculator.agi
todo-list.agi
hello-web.agi
```

## Phase B: Web developer

Learn:

```text
routes
controllers
AGS templates
forms
sessions
cookies
validation
404/500 pages
```

Build:

```text
personal website
blog
login dashboard
admin panel
```

## Phase C: API developer

Learn:

```text
JSON responses
API routes
validation
status codes
rate limits
API errors
```

Build:

```text
wallet API
merchant API
user profile API
AI capability API
```

## Phase D: Database developer

Learn:

```text
SQLite
models
migrations
indexes
transactions
safe SQL
```

Build:

```text
CRM
inventory app
payment ledger
merchant records
```

## Phase E: AIFlow developer

Learn:

```text
AGIRecord
image preprocessing
CNN training
BPE tokenizer
language model bundle
TorchCompat
ONNX bridge
GPU status
```

Build:

```text
document classifier
KYC helper
text categorizer
AI dashboard
```

## Phase F: Blockchain developer

Learn:

```text
chain ID
genesis
transactions
mempool
RPC
beacon
validators
consensus profile
```

Build:

```text
private chain
local RPC node
block explorer
wallet dashboard
validator simulation
```

## Phase G: Professional AGILANG developer

Learn:

```text
testing
security
deployment
CI/CD
monitoring
error handling
performance
architecture
```

Build:

```text
full-stack SaaS
AI-powered dashboard
private blockchain network
payment gateway prototype
production-ready web app
```

---

# Final professional rule

A professional AGILANG developer does not only write code. A professional developer:

```text
plans the structure
writes readable code
validates inputs
handles errors
writes tests
protects secrets
logs safely
checks deployment
updates documentation
keeps improving the runtime
```

That is the path from beginner to full-stack AGILANG developer.
