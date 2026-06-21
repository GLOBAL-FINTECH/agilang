# Security Guide

## Secrets

Use `.env`, not hardcoded keys.

```env
APP_SECRET=replace-with-long-random-secret
APP_API_TOKEN=replace-with-api-token
```

## Passwords

```agi
let password_hash = hash_password(password)
verify_password(password, password_hash)
```

## Signed Cookies

```agi
login_user(response, user, APP_SECRET, cookie_name=SESSION_COOKIE)
current_user(request, APP_SECRET, cookie_name=SESSION_COOKIE)
logout_user(response, cookie_name=SESSION_COOKIE)
```

## CSRF

Require CSRF for POST/PUT/PATCH/DELETE when using cookie sessions.

```agi
if not valid_api_csrf(request):
    return json_response({"ok": False, "error": "csrf_failed"}, status=403)
```
