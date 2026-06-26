# AGILANG Error Handling and Debugging Deep Reference

This guide teaches how to understand, simulate, collect, log, and fix errors in AGILANG applications.

It covers:

- syntax errors
- type errors
- route errors
- template errors
- database errors
- authentication errors
- validation errors
- 404 pages
- 500 pages
- error logging
- debugging workflow
- production incident checklist

---

## 1. Error categories

| Category | Example | Status code |
|---|---|---|
| Syntax error | invalid `.agi` indentation | compile/check failure |
| Type/check error | wrong return type | check/typecheck failure |
| Validation error | missing email | 422 |
| Auth error | not logged in | 401 or redirect |
| Permission error | non-admin accessing admin page | 403 |
| Not found | missing route/page/resource | 404 |
| Session expired | bad CSRF/session | 419 |
| Rate limit | too many login attempts | 429 |
| Server error | unhandled exception | 500 |

---

## 2. Syntax errors

Example broken code:

```agi
fn main() -> i32:
print("wrong indentation")
    return 0
```

Fix:

```agi
fn main() -> i32:
    print("correct indentation")
    return 0
```

Check:

```bash
agi check src/main.agi
agi typecheck src/main.agi
```

---

## 3. Import errors

Broken import:

```agi
import "src/missing.agi"
```

Fix:

```text
[ ] Confirm file exists
[ ] Confirm file path is correct
[ ] Confirm file extension is .agi
[ ] Confirm relative path is correct
```

Correct:

```agi
import "src/services/users.agi"
```

---

## 4. 404 Not Found

A 404 means the app could not find the requested route or resource.

Simulate:

```text
GET /this-route-does-not-exist
```

Common causes:

```text
missing route
wrong URL spelling
wrong HTTP method
missing route registration
missing static file
missing dynamic resource ID
```

Fix missing route:

```agi
fn register_web_routes(app):
    app.get("/about", about)
```

Fix wrong method:

```agi
app.post("/login", login_submit)
```

If the form says `method="POST"`, the route must be POST.

---

## 5. Custom 404 page

Template:

```ags
@page errors.404
@layout layout.ags

<h1>404 - Page not found</h1>
<p>The page you requested does not exist.</p>
<a href="/">Return home</a>
```

Controller:

```agi
fn not_found(request):
    return render_ags("errors/404.ags", {
        "title": "Page not found"
    }, 404)
```

Professional 404 page should include:

```text
clear title
short explanation
home link
search link if available
no internal stack trace
```

---

## 6. 500 Internal Server Error

A 500 means code failed while processing a request.

Simulate:

```agi
fn simulate_500(request):
    let value = 10 / 0
    return text_response("never reached")
```

Route:

```agi
app.get("/simulate-500", simulate_500)
```

Visit:

```text
/simulate-500
```

---

## 7. Fix division by zero

Broken:

```agi
fn price_per_item(total, qty):
    return total / qty
```

Fixed:

```agi
fn price_per_item(total, qty):
    if qty == 0:
        return {
            "ok": false,
            "error": "quantity_must_not_be_zero"
        }

    return {
        "ok": true,
        "value": total / qty
    }
```

---

## 8. Database errors

Common database errors:

```text
missing database file
missing table
wrong column name
unique constraint failure
SQL syntax error
unsafe string concatenation
locked database
```

Missing table example:

```text
no such table: users
```

Fix:

```text
[ ] Create migration
[ ] Run migration
[ ] Confirm storage/app.sqlite exists
[ ] Confirm table name matches query
```

Safe query:

```agi
db.first("SELECT * FROM users WHERE email = ?", [email])
```

---

## 9. Template errors

Common AGS template errors:

```text
missing .ags file
wrong template path
missing variable
raw HTML used unsafely
layout not found
```

Broken:

```agi
return render_ags("dashbord.ags", {"title": "Dashboard"})
```

Fix:

```agi
return render_ags("dashboard.ags", {"title": "Dashboard"})
```

---

## 10. Validation errors

Validation errors should normally return 422, not 500.

```agi
fn register_submit(request):
    let email = request.form("email")

    if email == "":
        return render_ags("register.ags", {
            "title": "Register",
            "error": "Email is required"
        }, 422)
```

Professional pattern:

```agi
fn validate_user(data):
    let errors = {}

    if data["name"] == "":
        errors["name"] = "Name is required"

    if data["email"] == "":
        errors["email"] = "Email is required"

    return errors
```

---

## 11. Authentication errors

Unauthenticated web page:

```agi
fn dashboard(request):
    let user_id = request.session_get("user_id")
    if user_id == null:
        return redirect("/login")

    return render_ags("dashboard.ags", {"title": "Dashboard"})
```

Unauthenticated API:

```agi
fn api_user(request):
    let user_id = request.session_get("user_id")
    if user_id == null:
        return json_response({
            "ok": false,
            "error": "unauthenticated"
        }, 401)
```

---

## 12. Permission errors

Non-admin user accessing admin page:

```agi
fn admin_dashboard(request):
    let user = current_user(request)

    if user == null:
        return redirect("/login")

    if user["role"] != "admin":
        return render_ags("errors/403.ags", {
            "title": "Forbidden"
        }, 403)

    return render_ags("admin/dashboard.ags", {"title": "Admin"})
```

---

## 13. Error logging

Create log folder:

```text
storage/logs/
```

Log format recommendation:

```json
{"level":"error","path":"/dashboard","message":"division by zero","time":"2026-06-26T10:00:00Z"}
```

Logger function:

```agi
fn log_error(error, request):
    let payload = {
        "level": "error",
        "path": request.path,
        "method": request.method,
        "message": str(error),
        "time": now()
    }

    file_append("storage/logs/errors.jsonl", json_encode(payload) + "\n")
```

---

## 14. Safe 500 wrapper

```agi
fn safe_handle(request, handler):
    try:
        return handler(request)
    except error:
        log_error(error, request)
        return render_ags("errors/500.ags", {
            "title": "Server error"
        }, 500)
```

Do not show stack traces to normal users in production.

---

## 15. API error format

```agi
fn api_error(code, message, status):
    return json_response({
        "ok": false,
        "error": {
            "code": code,
            "message": message
        }
    }, status)
```

Examples:

```agi
return api_error("not_found", "User not found", 404)
return api_error("validation_failed", "Invalid input", 422)
return api_error("server_error", "Something went wrong", 500)
```

---

## 16. Debugging route problems

Checklist:

```text
[ ] Is the route registered?
[ ] Is the route file imported?
[ ] Is the HTTP method correct?
[ ] Is the path spelling correct?
[ ] Is the controller function defined?
[ ] Does the controller return a response?
```

---

## 17. Debugging template problems

Checklist:

```text
[ ] Does resources/views/... exist?
[ ] Is the filename correct?
[ ] Is the layout path correct?
[ ] Did the controller pass every required variable?
[ ] Are user values escaped?
```

---

## 18. Debugging database problems

Checklist:

```text
[ ] Does the database file exist?
[ ] Did migrations run?
[ ] Does the table exist?
[ ] Does the column exist?
[ ] Is SQL parameterized?
[ ] Are values the expected type?
[ ] Is the database locked?
```

---

## 19. Debugging AIFlow problems

Checklist:

```text
[ ] Run agi ai doctor
[ ] Confirm dataset path exists
[ ] Confirm model path exists
[ ] Confirm JSON pixel input is valid
[ ] Confirm tokenizer file exists
[ ] Confirm optional onnxruntime if using real .onnx
[ ] Confirm GPU backend if require_gpu=true
```

Commands:

```bash
agi ai capabilities
agi ai doctor
agi ai onnx-status
agi ai gpu-status
python -m pytest tests/test_aiflow_production_upgrade.py
```

---

## 20. Debugging blockchain problems

Checklist:

```text
[ ] Check chain ID
[ ] Check genesis config
[ ] Check storage path
[ ] Check RPC host/port
[ ] Check account balance
[ ] Check transaction nonce
[ ] Check transaction value is not negative
[ ] Check validators are configured
[ ] Check beacon state
```

Commands:

```bash
agi chain status --root .
agi chain ethereum-consensus-check
agi beacon status
agi beacon simulate --validators 64 --epochs 2
```

---

## 21. Production incident checklist

When production fails:

```text
1. Confirm the error code
2. Check latest deployment commit
3. Check application logs
4. Check database health
5. Check storage permissions
6. Check environment variables
7. Check external services
8. Reproduce in staging
9. Add a regression test
10. Deploy a small fix
11. Document the incident
```

---

## 22. Error response principles

Good error response:

```json
{
  "ok": false,
  "error": {
    "code": "validation_failed",
    "message": "Email is required"
  }
}
```

Bad error response:

```text
Traceback: internal file paths and secrets...
```

Never expose:

```text
passwords
private keys
API tokens
database credentials
full server paths
raw stack traces to public users
```

---

## 23. Add tests for errors

Every important error should have a test:

```text
unknown route returns 404
invalid form returns 422
unauthenticated API returns 401
forbidden admin route returns 403
simulated server error returns 500 and logs error
```

---

## Final rule

Errors are not failure. Unhandled, undocumented, untested errors are failure.

Professional AGILANG code should detect errors early, return clear responses, log safely, and include tests.
