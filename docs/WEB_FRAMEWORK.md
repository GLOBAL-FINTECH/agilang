# AGILANG Web Framework Runtime

AGILANG v0.8 introduces `agilang.web`, a dependency-free HTTP framework for the Python backend.

## App creation

```agi
let app = web_app("my-app", True)
```

## Routes

```agi
fn home(request):
    return html_response("<h1>Hello</h1>")

fn show_user(request):
    return json_response({"id": request.params["id"]})

app.get("/", home)
app.get("/users/<id>", show_user)
```

## Request data

- `request.params`
- `request.query`
- `request.headers`
- `request.text`
- `request.json({})`
- `request.form`
- `request.cookies`
- `request.input("name", default)`

## Responses

- `text_response("ok")`
- `html_response("<h1>ok</h1>")`
- `json_response({"ok": True})`
- `redirect("/login")`
- `file_response("public/report.pdf")`

## Static files

```agi
app.static("/assets", "public")
```

## Templates

```agi
return html_response(render_template("<h1>{{ title }}</h1>", {"title": "Dashboard"}))
```

`{{ value }}` is escaped. `{{{ value }}}` inserts trusted raw HTML.

## Security helpers

```agi
let password_hash = hash_password("secret")
let ok = verify_password("secret", password_hash)
let token = sign_cookie({"user_id": "u1"}, "dev-secret", 3600)
let session = verify_cookie(token, "dev-secret")
```

## SQLite helper

```agi
let db = sqlite_db("app.db")
db.execute("create table users(id integer primary key, name text)")
db.execute("insert into users(name) values (?)", ["Ada"])
let user = db.one("select * from users where id = ?", [1])
```

## Serve command

```bash
agilang serve src/main.agi --host 127.0.0.1 --port 9000
```

The source can define `app`, `application`, `create_app()`, or return an app from `main()`.
