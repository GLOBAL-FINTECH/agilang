# AGILANG Web, Database, Authentication, and API Deep Reference

This document teaches professional full-stack AGILANG application development: routes, controllers, views, forms, sessions, authentication, database access, APIs, middleware, security, and deployment structure.

---

## 1. Professional web project structure

Recommended layout:

```text
my-app/
├─ agilang.toml
├─ src/
│  ├─ main.agi
│  ├─ services/
│  │  ├─ auth.agi
│  │  ├─ users.agi
│  │  └─ dashboard.agi
├─ routes/
│  ├─ web.agi
│  └─ api.agi
├─ app/
│  ├─ controllers/
│  │  ├─ HomeController.agi
│  │  ├─ AuthController.agi
│  │  ├─ UserController.agi
│  │  └─ ApiController.agi
│  └─ models/
│     ├─ User.agi
│     └─ AuditLog.agi
├─ resources/views/
├─ config/
├─ database/migrations/
├─ storage/
└─ tests/
```

---

## 2. Application boot file

`src/main.agi`:

```agi
import "routes/web.agi"
import "routes/api.agi"

fn main() -> i32:
    let app = web_app()
    register_web_routes(app)
    register_api_routes(app)
    app.serve("127.0.0.1", 8000)
    return 0
```

---

## 3. Web routes

`routes/web.agi`:

```agi
import "app/controllers/HomeController.agi"
import "app/controllers/AuthController.agi"
import "app/controllers/DashboardController.agi"

fn register_web_routes(app):
    app.get("/", home)
    app.get("/login", login_page)
    app.post("/login", login_submit)
    app.post("/logout", logout)
    app.get("/dashboard", dashboard)
```

Professional route groups:

```agi
fn register_admin_routes(app):
    app.get("/admin", admin_dashboard)
    app.get("/admin/users", admin_users)
```

---

## 4. API routes

`routes/api.agi`:

```agi
import "app/controllers/ApiController.agi"

fn register_api_routes(app):
    app.get("/api/health", api_health)
    app.get("/api/user", api_user)
    app.post("/api/users", api_create_user)
```

API rule: return JSON, not HTML.

```agi
fn api_health(request):
    return json_response({
        "ok": true,
        "service": "agilang-api"
    })
```

---

## 5. Controllers

Controller example:

```agi
fn home(request):
    return render_ags("home.ags", {
        "title": "Home"
    })
```

A controller should:

```text
1. read request data
2. validate input
3. call service/model functions
4. return view, redirect, or JSON
```

Bad controller:

```agi
fn register(request):
    # huge SQL, validation, email sending, template rendering all mixed together
```

Good controller:

```agi
fn register_submit(request):
    let data = register_input(request)
    let result = create_user_account(data)

    if result["ok"] == false:
        return render_ags("register.ags", {
            "title": "Register",
            "errors": result["errors"],
            "old": data
        }, 422)

    return redirect("/login")
```

---

## 6. Request input

Common request sources:

```agi
request.form("email")
request.query("page")
request.params("id")
request.json()
request.session_get("user_id")
```

Always validate request input before using it.

---

## 7. Responses

HTML response:

```agi
return render_ags("home.ags", {"title": "Home"})
```

JSON response:

```agi
return json_response({"ok": true})
```

Redirect:

```agi
return redirect("/dashboard")
```

Status code:

```agi
return json_response({"ok": false, "error": "not_found"}, 404)
```

---

## 8. Database configuration

`config/database.json`:

```json
{
  "driver": "sqlite",
  "database": "storage/app.sqlite"
}
```

Professional rule: never hardcode production credentials inside source files.

---

## 9. Migrations

Example migration:

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

Audit log table:

```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    created_at TEXT NOT NULL
);
```

---

## 10. Safe SQL

Bad:

```agi
let sql = "SELECT * FROM users WHERE email = '" + email + "'"
let user = db.first(sql)
```

Good:

```agi
let user = db.first("SELECT * FROM users WHERE email = ?", [email])
```

Safe insert:

```agi
fn create_user(name, email, password_hash):
    return db.execute(
        "INSERT INTO users (name, email, password_hash, created_at, updated_at) VALUES (?, ?, ?, datetime('now'), datetime('now'))",
        [name, email, password_hash]
    )
```

---

## 11. Model-style functions

`app/models/User.agi`:

```agi
fn user_find_by_id(id):
    return db.first("SELECT * FROM users WHERE id = ?", [id])

fn user_find_by_email(email):
    return db.first("SELECT * FROM users WHERE email = ?", [email])

fn user_create(data):
    return db.execute(
        "INSERT INTO users (name, email, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
        [data["name"], data["email"], data["password_hash"], data["role"]]
    )
```

---

## 12. Authentication flow

Authentication steps:

```text
1. GET /login shows login form
2. POST /login validates credentials
3. password is verified
4. session is created
5. user is redirected to dashboard
6. protected routes check session
7. POST /logout removes session
```

Login page:

```agi
fn login_page(request):
    return render_ags("login.ags", {
        "title": "Login",
        "old": {"email": ""},
        "error": ""
    })
```

Login submit:

```agi
fn login_submit(request):
    let email = request.form("email")
    let password = request.form("password")

    if email == "" or password == "":
        return render_ags("login.ags", {
            "title": "Login",
            "old": {"email": email},
            "error": "Email and password are required"
        }, 422)

    let user = user_find_by_email(email)
    if user == null:
        return render_ags("login.ags", {
            "title": "Login",
            "old": {"email": email},
            "error": "Invalid login details"
        }, 401)

    if not verify_password(password, user["password_hash"]):
        return render_ags("login.ags", {
            "title": "Login",
            "old": {"email": email},
            "error": "Invalid login details"
        }, 401)

    request.session_set("user_id", user["id"])
    return redirect("/dashboard")
```

Logout:

```agi
fn logout(request):
    request.session_delete("user_id")
    return redirect("/login")
```

---

## 13. Authorization

Authentication answers: who are you?

Authorization answers: what are you allowed to do?

```agi
fn require_admin(request):
    let user = current_user(request)
    if user == null:
        return redirect("/login")

    if user["role"] != "admin":
        return render_ags("errors/403.ags", {"title": "Forbidden"}, 403)

    return null
```

---

## 14. Sessions

Session usage:

```agi
request.session_set("user_id", user["id"])
let user_id = request.session_get("user_id")
request.session_delete("user_id")
```

Professional session rules:

```text
[ ] Rotate session after login
[ ] Use secure cookies in production
[ ] Use HTTP-only cookies
[ ] Set SameSite policy
[ ] Do not store passwords or private keys in session
```

---

## 15. CSRF protection

Every form that changes data should use CSRF protection.

Template concept:

```ags
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
```

Controller concept:

```agi
if not csrf_valid(request):
    return render_ags("errors/419.ags", {"title": "Session expired"}, 419)
```

---

## 16. Middleware

Auth middleware:

```agi
fn auth_middleware(request, next):
    let user_id = request.session_get("user_id")
    if user_id == null:
        return redirect("/login")
    return next(request)
```

API auth middleware:

```agi
fn api_auth_middleware(request, next):
    let token = request.header("Authorization")
    if token == null:
        return json_response({"ok": false, "error": "missing_token"}, 401)
    return next(request)
```

---

## 17. JSON API design

Standard successful response:

```json
{
  "ok": true,
  "data": {},
  "error": null
}
```

Standard failed response:

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "validation_failed",
    "message": "Please check the submitted fields"
  }
}
```

Controller:

```agi
fn api_create_user(request):
    let data = request.json()
    let result = create_user_account(data)

    if result["ok"] == false:
        return json_response(result, 422)

    return json_response(result, 201)
```

---

## 18. Status codes

| Code | Meaning | AGILANG use |
|---|---|---|
| 200 | OK | normal response |
| 201 | Created | resource created |
| 302 | Redirect | login/logout redirects |
| 400 | Bad request | malformed input |
| 401 | Unauthenticated | login required |
| 403 | Forbidden | no permission |
| 404 | Not found | missing route/resource |
| 419 | Session expired | CSRF/session issue |
| 422 | Validation failed | form/API validation |
| 429 | Too many requests | rate limit |
| 500 | Server error | unhandled exception |

---

## 19. Rate limiting

Login endpoint should be rate-limited.

```agi
fn login_submit(request):
    if rate_limited(request.ip, "login"):
        return render_ags("login.ags", {
            "title": "Login",
            "error": "Too many attempts. Try again later."
        }, 429)
```

---

## 20. Audit logging

Audit important actions:

```agi
fn audit(user_id, action, request):
    db.execute(
        "INSERT INTO audit_logs (user_id, action, ip_address, user_agent, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
        [user_id, action, request.ip, request.header("User-Agent")]
    )
```

Audit examples:

```text
user_login
user_logout
password_changed
profile_updated
admin_user_disabled
payment_created
api_key_created
```

---

## 21. Full-stack example route map

```text
GET  /                  home
GET  /login             login_page
POST /login             login_submit
POST /logout            logout
GET  /dashboard         dashboard
GET  /users             users_index
GET  /users/create      users_create
POST /users             users_store
GET  /api/health        api_health
GET  /api/user          api_user
POST /api/users         api_create_user
```

---

## 22. Deployment checklist

```text
[ ] Database file exists or migrations run
[ ] storage/ is writable
[ ] logs are private
[ ] .env values are set
[ ] debug mode disabled
[ ] secure cookies enabled
[ ] CSRF enabled
[ ] rate limits enabled
[ ] admin routes protected
[ ] API tokens protected
[ ] backups configured
[ ] error pages exist
[ ] tests pass
```

---

## 23. Professional full-stack exercise

Build:

```text
AGILANG CRM Lite
```

Features:

```text
register/login/logout
dashboard
users table
create user
edit user
delete user
API health
custom 404
custom 500
audit logs
```

Required tests:

```text
homepage loads
login validation works
invalid login returns 401
protected dashboard redirects guest
API health returns ok
missing route returns 404
simulate-500 logs error
```

---

## Final rule

A professional AGILANG web app separates:

```text
routes -> controllers -> services/models -> views/API responses
```

Do not mix everything into one file once the app grows.
