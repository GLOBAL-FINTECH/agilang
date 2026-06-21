# API Guide

## JSON API

```agi
fn api_status(request):
    return json_response({"ok": True, "status": "online"})

app.get("/api/status", api_status)
```

## API With Validation

```agi
fn api_create_post(request):
    let title = request.input("title", "")
    if title == "":
        return json_response({"ok": False, "error": "title_required"}, status=422)
    return json_response({"ok": True, "title": title}, status=201)

app.post("/api/posts", api_create_post)
```

## API Auth Pattern

```agi
fn require_session_api(request):
    let user = current_user(request, APP_SECRET, cookie_name=SESSION_COOKIE)
    if user == None:
        return json_response({"ok": False, "error": "authentication_required"}, status=401)
    request.user = user
    return None
```
