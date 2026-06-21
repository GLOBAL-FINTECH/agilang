# AGILANG Documentation Scan Report

## Scan Target

Scanned package: `AGILANG_v2_1_social_network_suite.zip` extracted as `devapp`.

Detected runtime version:

```text
AGILANG 2.1.0
```

Validation commands executed:

```bash
PYTHONPATH=docs python -m agilang --version
PYTHONPATH=docs python -m agilang doctor
PYTHONPATH=docs python -m agilang check src tests
PYTHONPATH=docs python -m agilang test
```

Result:

```text
version: passed
runtime doctor: passed
check: passed with warnings only, exit code 0
test: passed
```

---

## Important Findings

### 1. Correct Split-File Keyword

The actual translator supports:

```agi
import "file.agi"
```

It does **not** currently implement:

```agi
include "file.agi"
```

Documentation should teach `import`, not `include`.

---

### 2. AGS Templates Are Supported

The runtime supports `.ags` files through:

```agi
render_ags("../resources/views/home.ags", context)
```

Supported AGS directives found in the runtime:

```ags
@page title="..." seo_description="..."
@layout "layout.ags"
@fetch stats from "/api/home-stats"
@live stats from "/api/home-stats" every 5000
@state
```

Automatic live binding is implemented for dotted expressions such as:

```ags
{{ stats.users }}
{{ stats.items }}
{{ stats.status }}
```

These are converted into browser-bound spans using `data-ags-live` or `data-ags-fetch`.

---

### 3. CLI Commands Present

The CLI exposes these top-level commands:

```text
run
check
to-py
build
fmt
new
make:page
make:component
make:api
test-examples
test
tokens
ast
typecheck
to-c
native-build
backends
lsp
pkg
db
react
runtime
mobile
hosting
net
evm
zk
systems
blockchain
serve
doctor
repl
```

Full documentation has been added in `docs/CLI_REFERENCE.md`.

---

### 4. Web Runtime Features Found

The `web.py` runtime supports:

- `web_app()`
- `app.get()`
- `app.post()`
- `app.put()`
- `app.delete()`
- `app.any()`
- route parameters like `/posts/<id>`
- middleware groups
- before/after handlers
- static file mounts
- threaded development server
- WSGI adapter
- ASGI adapter
- HTML responses
- JSON responses
- redirects
- file responses
- secure cookies
- password hashing
- CSRF helpers
- SQLite helper
- MySQL helper
- validation helper
- simple model/ORM helper
- background job queue

---

### 5. Current Starter App Routes

The social network suite registers these page routes:

```text
GET  /
GET  /home
GET  /about
GET  /blog
GET  /news
GET  /posts/<id>
GET  /social
GET  /videos
GET  /dating
GET  /routes
GET  /billing
GET  /login
GET  /register
GET  /dashboard
GET  /profile
GET  /security
GET  /evm
GET  /payments/success
GET  /payments/cancel
POST /payments/stripe/checkout
POST /payments/paypal/checkout
POST /login
POST /register
POST /profile
POST /security/email
POST /security/password
POST /evm
POST /posts
POST /posts/<id>/status
POST /posts/<id>/delete
POST /logout
GET  /health
```

API routes:

```text
GET    /api/me
GET    /api/home-stats
PUT    /api/profile
PUT    /api/security/email
PUT    /api/security/password
GET    /api/evm/status
POST   /api/evm/probe
GET    /api/users
PUT    /api/users/<id>/role
GET    /api/posts
POST   /api/posts
GET    /api/posts/<id>
PUT    /api/posts/<id>
DELETE /api/posts/<id>
GET    /api/social/profile
PUT    /api/social/profile
GET    /api/social-feed
POST   /api/social/posts
POST   /api/social/posts/<id>/like
GET    /api/social/people
POST   /api/social/follow/<id>
POST   /api/social/friend-request/<id>
GET    /api/social/messages
POST   /api/social/messages
GET    /api/video-feed
POST   /api/videos
GET    /api/dating/suggestions
PUT    /api/dating/profile
POST   /api/dating/like/<id>
GET    /api/routes
```

---

## Documentation Files Needed for a Professional GitHub Repository

The repository should contain these documents:

```text
README.md
LICENSE
CHANGELOG.md
CONTRIBUTING.md
SECURITY.md
CODE_OF_CONDUCT.md
docs/CLI_REFERENCE.md
docs/SYNTAX_REFERENCE.md
docs/AGS_TEMPLATES.md
docs/WEB_APP_GUIDE.md
docs/SPLIT_FILE_ARCHITECTURE.md
docs/API_GUIDE.md
docs/DATABASE_GUIDE.md
docs/AUTH_SECURITY_GUIDE.md
docs/PAYMENTS_EXAMPLES.md
docs/DEBUGGING_ERRORS.md
docs/SOCIAL_NETWORK_GUIDE.md
docs/DEPLOYMENT_GUIDE.md
docs/BLOCKCHAIN_GUIDE.md
docs/EVM_GUIDE.md
docs/ZK_GUIDE.md
docs/WEBRTC_REALTIME_GUIDE.md
docs/ML_GUIDE.md
examples/
tests/
.github/workflows/ci.yml
```

---

## Documentation Corrections Required

### Replace “young language” wording

Use:

```text
AGILANG is a programming language and application framework.
```

Do not use:

```text
young language
```

### Use MIT license wording

```text
MIT License
Copyright (c) Izukanji Sirwimba, AGILab, Izurex Center Place Limited
```

### Use `.ags` as default template docs

Do not teach old default HTML templates as the primary path. HTML can be mentioned only as optional static content.

### Teach `import`, not `include`

The actual translator implements AGILANG file linking through:

```agi
import "../controllers/HomeController.agi"
```

---

## Static Check Warnings Observed

`agilang check src tests` exits successfully but reports warnings. Most warnings come from type inference limitations, especially functions without explicit return annotations.

Recommended coding style:

```agi
fn strong_password(password) -> bool:
    return len(password) >= 8

fn normalize_role(role) -> string:
    if role == "admin":
        return "admin"
    return "member"
```

This reduces warnings like:

```text
Return type mismatch: expected void, got bool
Return type mismatch: expected void, got str
```

Recommended docs note: teach beginners to add return types for helper functions.

---

## Debugging Commands to Document Prominently

```bash
agilang check src tests
agilang run src/main.agi --check
agilang run src/main.agi --dump
agilang to-py src/main.agi --line-map
agilang tokens src/main.agi
agilang ast src/main.agi --pretty
agilang typecheck src tests
agilang doctor
```

---

## Final Recommendation

The GitHub documentation should be organized around developer workflows:

1. Install AGILANG
2. Create a project
3. Understand `.agi` syntax
4. Understand `.ags` templates
5. Create routes
6. Create JSON APIs
7. Use databases
8. Add authentication
9. Split app code into files
10. Debug errors
11. Add payments
12. Deploy locally and on hosting
13. Build blockchain/Web3 modules
14. Contribute to the language
