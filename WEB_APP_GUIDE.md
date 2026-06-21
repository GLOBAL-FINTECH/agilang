# AGILANG Web App Guide

## Create an App

```agi
fn create_app():
    let app = web_app("myapp", True)
    app.static("/assets", "../resources/assets")
    return app
```

## Routes

```agi
fn home(request):
    return html_response("<h1>Home</h1>")

fn health(request):
    return json_response({"ok": True})

app.get("/", home)
app.get("/health", health)
```

## Route Parameters

```agi
fn show_post(request):
    let id = request.input("id", "")
    return json_response({"id": id})

app.get("/posts/<id>", show_post)
```

## Middleware

```agi
fn require_auth(request):
    let user = current_user(request, APP_SECRET, cookie_name=SESSION_COOKIE)
    if user == None:
        return redirect("/login")
    request.user = user
    return None

app.get("/dashboard", dashboard, middleware=require_auth)
```

## After Handler for Security Headers

```agi
fn secure_response(request, response):
    response.set_header("X-Frame-Options", "DENY")
    response.set_header("X-Content-Type-Options", "nosniff")
    return response

app.after(secure_response)
```

## Serve

```bash
agilang serve src/main.agi --host 127.0.0.1 --port 8000
```
