# AGILANG v0.9 Web Platform Edition

AGILANG v0.9 extends the v0.8 HTTP/WebSocket framework with a Laravel-style application layer for the Python backend.

## Runtime capabilities

- ORM/model layer backed by SQLite
- migrations table and idempotent migration runner
- validation schemas with required/email/min/max/int/number/in rules
- CSRF token creation, hidden-input helper and CSRF middleware
- signed-cookie authentication helpers
- route middleware and named middleware groups
- in-process background jobs/queues
- WSGI adapter for Gunicorn/uWSGI-compatible deployment
- ASGI adapter for Uvicorn/Hypercorn-compatible HTTP deployment
- experimental native C HTTP runtime source and WebSocket ABI placeholders

## ORM / models

```agi
let db = sqlite_db("app.db")
let User = model("User", {
    "id": integer(primary_key=True, nullable=False),
    "email": string(nullable=False, unique=True),
    "name": string(nullable=False)
})

fn create_users(db):
    User.create_table(db)

migrate(db, [("001_create_users", create_users)])
User(email="ada@example.com", name="Ada").save(db)
let user = User.where(db, email="ada@example.com").first()
```

## Validation

```agi
let result = validate(request.json({}), {
    "email": "required|email",
    "name": "required|min:2|max:80"
})

if not result.ok:
    return json_response({"errors": result.errors}, status=422)
```

## CSRF and auth middleware

```agi
let secret = "change-me"
let app = web_app("secure", False)
app.middleware_group("secure", [auth_required(secret), csrf_protect(secret)])

fn dashboard(request):
    return json_response({"user": request.user})

app.post("/dashboard", dashboard, middleware="secure")
```

## Background jobs

```agi
let jobs = job_queue(2)

fn send_report(email):
    return "report-ready:" + email

let job_id = jobs.enqueue(send_report, "merchant@example.com")
```

## Production adapters

Python servers can import the AGILANG-generated Python launcher and use:

```python
from app import create_app
from agilang.web import wsgi_adapter, asgi_adapter

app = create_app()
application = wsgi_adapter(app)   # WSGI
asgi_app = asgi_adapter(app)      # ASGI HTTP
```

## Production status

The Python backend has the complete v0.9 web platform layer. The native C runtime includes a compileable HTTP server runtime and WebSocket ABI placeholders. Full native C WebSocket frame handling, TLS, router integration and event loop parity remain tracked in `docs/C_NATIVE_HTTP_WEBSOCKET_RUNTIME.md`.
