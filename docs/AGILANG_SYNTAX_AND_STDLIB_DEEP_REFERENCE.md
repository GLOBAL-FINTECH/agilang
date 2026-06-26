# AGILANG Syntax and Standard Library Deep Reference

This reference expands the beginner wiki into a deeper language manual. It explains the AGILANG syntax surface, common built-in patterns, data structures, modules, CLI checks, and professional coding habits.

> Status note: AGILANG is evolving. This document separates stable practical usage from planned/deeper areas. When a feature is not guaranteed, the documentation says so rather than pretending it is complete.

---

## 1. Source files

AGILANG code is written in `.agi` files.

```text
src/main.agi
src/users.agi
src/services/payments.agi
```

A file normally contains functions, constants, structs, enums and imports.

```agi
import "src/users.agi"

const APP_NAME = "AGILANG App"

fn main() -> i32:
    print(APP_NAME)
    return 0
```

---

## 2. Comments

Use `#` for comments.

```agi
# This function starts the application
fn main() -> i32:
    print("Booting...")
    return 0
```

Professional habit: comments should explain why code exists, not repeat obvious code.

Good:

```agi
# Prevent duplicate webhook processing from retry events
fn already_processed(event_id) -> bool:
    return db.exists("SELECT id FROM webhooks WHERE event_id = ?", [event_id])
```

Bad:

```agi
# Add one to count
count = count + 1
```

---

## 3. Indentation

AGILANG uses indentation to define blocks.

Correct:

```agi
fn check(active) -> str:
    if active:
        return "active"
    else:
        return "inactive"
```

Wrong:

```agi
fn check(active) -> str:
if active:
return "active"
```

If indentation is wrong, the parser may fail or the code may behave incorrectly.

---

## 4. Variables

Use `let` for normal variables.

```agi
let name = "Alice"
let age = 25
let active = true
```

Variables can be reassigned:

```agi
let count = 1
count = count + 1
```

Professional rule: use clear variable names.

Good:

```agi
let merchant_balance = 1500
```

Bad:

```agi
let x = 1500
```

---

## 5. Constants

Use `const` for values that should not change.

```agi
const APP_NAME = "AGILANG CRM"
const DEFAULT_PAGE_SIZE = 20
const MAX_LOGIN_ATTEMPTS = 5
```

Use uppercase names for constants.

---

## 6. Primitive values

### Strings

```agi
let message = "Welcome"
```

### Integers

```agi
let users_count = 10
```

### Floats

```agi
let price = 19.99
```

### Booleans

```agi
let is_admin = false
let active = true
```

### Null-style values

When representing a missing value, use the runtime-supported null/none pattern used by the current AGILANG host runtime.

```agi
let user = null
```

Check null before access:

```agi
if user == null:
    return redirect("/login")
```

---

## 7. Strings

Basic string usage:

```agi
let first = "AGI"
let second = "LANG"
let name = first + second
```

Common operations to use through the host/runtime when available:

```agi
len(name)
str(value)
```

Recommended helper functions for app code:

```agi
fn is_empty(value) -> bool:
    return value == null or value == ""

fn normalize_email(email) -> str:
    return lower(trim(email))
```

If a specific string helper is not yet documented in the runtime, create a small helper wrapper and test it.

---

## 8. Lists

Create a list:

```agi
let users = ["Alice", "Bob", "Carol"]
```

Loop over a list:

```agi
for user in users:
    print(user)
```

Access by index when supported by the runtime:

```agi
let first_user = users[0]
```

Professional helper patterns:

```agi
fn find_active_users(users):
    let result = []
    for user in users:
        if user["active"] == true:
            result.append(user)
    return result
```

If methods like `append`, `push`, `pop`, `map`, or `filter` differ in the runtime version, prefer explicit loops until the standard library reference for that version confirms the exact names.

---

## 9. Dictionaries / maps

Use dictionaries for key-value data.

```agi
let user = {
    "name": "Alice",
    "email": "alice@example.com",
    "active": true
}
```

Read values:

```agi
let email = user["email"]
```

Update values:

```agi
user["active"] = false
```

Professional use cases:

```agi
let response = {
    "ok": true,
    "message": "User created"
}
```

---

## 10. Functions

Basic function:

```agi
fn greet(name) -> str:
    return "Hello " + name
```

Function with validation:

```agi
fn calculate_total(price, qty):
    if qty <= 0:
        return {
            "ok": false,
            "error": "invalid_quantity"
        }

    return {
        "ok": true,
        "total": price * qty
    }
```

Professional rules:

- one function should do one job
- validate inputs at the top
- return predictable shapes
- avoid hidden side effects
- write tests for important functions

---

## 11. Return values

Return a simple value:

```agi
fn add(a, b) -> i32:
    return a + b
```

Return a dictionary for business operations:

```agi
fn create_invoice(data):
    if data["amount"] <= 0:
        return {"ok": false, "error": "invalid_amount"}

    let invoice = db.insert("invoices", data)
    return {"ok": true, "invoice": invoice}
```

This pattern is good for services.

---

## 12. Conditions

```agi
if role == "admin":
    return "allowed"
elif role == "manager":
    return "limited"
else:
    return "denied"
```

Use guard clauses for cleaner code:

```agi
fn dashboard(request):
    let user_id = request.session_get("user_id")
    if user_id == null:
        return redirect("/login")

    return render_ags("dashboard.ags", {"title": "Dashboard"})
```

---

## 13. Loops

For loop:

```agi
for item in items:
    print(item)
```

While loop:

```agi
let i = 0
while i < 10:
    print(i)
    i = i + 1
```

Avoid infinite loops:

```agi
while true:
    # only use in supervised services with clear stop conditions
```

---

## 14. Structs

Structs describe grouped data.

```agi
struct User:
    id: i32
    name: str
    email: str
    active: bool
```

Use structs to document expected data shape.

---

## 15. Enums

Enums describe limited states.

```agi
enum OrderStatus:
    PENDING
    PAID
    CANCELLED
```

Good for:

- transaction status
- user roles
- payment status
- blockchain transaction state
- AI job state

---

## 16. Imports

Import another AGILANG file:

```agi
import "src/auth.agi"
import "src/services/users.agi"
```

Professional module layout:

```text
src/
├─ main.agi
├─ auth.agi
├─ services/
│  ├─ users.agi
│  └─ payments.agi
└─ support/
   └─ validation.agi
```

---

## 17. Error handling

Use `try` / `except` around risky operations.

```agi
fn read_config(path):
    try:
        return json_read(path)
    except error:
        return {
            "ok": false,
            "error": "config_read_failed",
            "message": str(error)
        }
```

Professional pattern:

```agi
fn service_result(ok, data, error):
    return {
        "ok": ok,
        "data": data,
        "error": error
    }
```

---

## 18. File and JSON helpers

Common patterns used across AGILANG apps:

```agi
let config = json_read("config/app.json")
file_append("storage/logs/app.log", "started\n")
let payload = json_encode({"ok": true})
```

Recommended project files:

```text
config/app.json
config/database.json
storage/logs/app.log
storage/cache/
```

Always validate JSON before deployment:

```bash
python -m json.tool config/app.json
```

---

## 19. Date and time patterns

Typical timestamp usage:

```agi
let created_at = now()
```

Store timestamps in a consistent format. Recommended:

```text
UTC ISO-8601
```

Example database field:

```sql
created_at TEXT NOT NULL
```

---

## 20. Standard response pattern

Use a consistent result format.

```agi
fn ok(data):
    return {"ok": true, "data": data, "error": null}

fn fail(code, message):
    return {"ok": false, "data": null, "error": {"code": code, "message": message}}
```

Use this in services, APIs, AI jobs, and blockchain tasks.

---

## 21. CLI checking workflow

Before committing code:

```bash
agi check src/main.agi
agi typecheck src/main.agi
python -m compileall -q agilang tests
python -m pytest
```

For AIFlow work:

```bash
agi ai doctor
python -m pytest tests/test_aiflow_production_upgrade.py
```

For blockchain work:

```bash
agi chain status --root .
agi chain ethereum-consensus-check
```

---

## 22. Unsupported or evolving features

Do not assume these are complete unless the current code and tests confirm them:

```text
full object-oriented inheritance
interfaces/traits
generics
async/await
native GPU execution without an installed backend
full PyTorch parity
full ONNX operator coverage
full Ethereum mainnet client parity
```

Use the capability commands:

```bash
agi ai capabilities
agi ai doctor
agi chain ethereum-consensus-capabilities
```

---

## 23. Professional style guide

Use clear file names:

```text
AuthController.agi
UserService.agi
PaymentService.agi
```

Use clear function names:

```agi
fn create_user_account(data):
fn validate_payment_request(data):
fn calculate_agent_commission(amount):
```

Avoid vague names:

```agi
fn do_it(x):
fn handle(data):
fn process2(a):
```

---

## 24. Production readiness checklist

```text
[ ] Code passes syntax checks
[ ] Code passes tests
[ ] Inputs are validated
[ ] Errors are handled
[ ] Logs do not expose secrets
[ ] SQL uses parameters
[ ] Routes are protected
[ ] Storage folders are writable
[ ] Config is documented
[ ] README is updated
```

---

## 25. Learning exercises

1. Write `hello.agi`.
2. Write a calculator with `add`, `subtract`, `multiply`, `divide`.
3. Create a list of users and print active users.
4. Create a dictionary response with `ok`, `data`, and `error`.
5. Create a safe division function that returns an error instead of crashing.
6. Split code into `src/main.agi` and `src/users.agi`.
7. Add tests for your service functions.

---

## Final summary

This document is the deep syntax and standard-library-style guide. Use it together with:

```text
docs/AGILANG_BEGINNER_TO_PROFESSIONAL_WIKI.md
docs/AGILANG_WEB_DATABASE_AUTH_DEEP_REFERENCE.md
docs/AGILANG_AGS_TEMPLATE_DEEP_REFERENCE.md
docs/AGILANG_ERROR_DEBUGGING_DEEP_REFERENCE.md
docs/AGILANG_AI_BLOCKCHAIN_DEEP_REFERENCE.md
```
