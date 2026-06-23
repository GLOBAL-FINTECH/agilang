# AGILANG Language Guide

AGILANG uses readable `.agi` source files for application logic, CLI scripts, backend services, web routes, and blockchain runtime scripts.

## Hello world

```agi
fn main() -> i32:
    print("Hello from AGILANG")
    return 0
```

Run:

```bash
agi run hello.agi
```

## Comments

```agi
# This is a comment
```

## Variables and constants

```agi
let name = "AGILANG"
let count: i32 = 10
const APP_NAME = "My App"
```

Use `let` for variables and `const` for values that should not change.

## Functions

```agi
fn add(a: i32, b: i32) -> i32:
    return a + b

fn greet(name: string) -> string:
    return "Hello, " + name
```

## Conditionals

```agi
if role == "admin":
    print("Admin")
elif role == "editor":
    print("Editor")
else:
    print("User")
```

## Loops

```agi
for name in ["Amina", "John", "Mary"]:
    print(name)
```

## Structs

```agi
struct User:
    id: i32
    name: string
    email: string
```

## Enums

```agi
enum PostStatus:
    DRAFT
    PUBLISHED
    ARCHIVED
```

## Type aliases

```agi
type UserId = i64
let id: UserId = 1001
```

## Imports

Split applications into files and import them:

```agi
import "config.agi"
import "routes/web.agi"
import "services/mail.agi"
```

Recommended app structure:

```text
src/
├─ main.agi
├─ config.agi
├─ routes/
│  ├─ web.agi
│  └─ api.agi
├─ controllers/
├─ services/
└─ middleware/
```

## Web routes

```agi
fn home(request):
    return html_response("<h1>Welcome</h1>")

fn api_health(request):
    return json_response({"ok": True})

fn create_app():
    let app = web_app("myapp", True)
    app.get("/", home)
    app.get("/api/health", api_health)
    return app
```

Serve:

```bash
agi serve src/main.agi --host 127.0.0.1 --port 8000
```

## JSON responses

```agi
fn profile_api(request):
    return json_response({
        "ok": True,
        "user": {
            "name": "AGILANG Developer",
            "role": "admin"
        }
    })
```

## AGS templates

AGS templates live in `resources/views`.

```ags
@page title="Home" seo_description="AGILANG app home page."
@layout "layout.ags"

<section class="hero">
  <h1>{{ app_name }}</h1>
  <p>{{ message }}</p>
</section>
```

Render from `.agi`:

```agi
fn home_page(request):
    let view = render_ags("../resources/views/home.ags", {
        "app_name": "AGILANG",
        "message": "Build web apps, APIs, and blockchain tools."
    })
    return html_response(view["body"])
```

## Database helper pattern

```agi
const DB_PATH = "../storage/app.sqlite"

fn db():
    ensure_dir("../storage")
    return sqlite_db(DB_PATH)

fn migrate(app_db):
    app_db.execute("create table if not exists posts (id integer primary key autoincrement, title text not null, body text not null)")
```

## Error handling

```agi
fn safe_api(request):
    try:
        return json_response({"ok": True})
    except Exception as exc:
        return json_response({"ok": False, "error": str(exc)}, status=500)
```

## Beginner exercises

1. Create `hello.agi` and print your name.
2. Create a function that returns a greeting.
3. Create a small web app with `/` and `/api/health`.
4. Create an `.ags` template and render it.
5. Create a SQLite table and return records as JSON.
6. Generate a blockchain app and inspect `src/chain.agi` and `config/network.json`.
