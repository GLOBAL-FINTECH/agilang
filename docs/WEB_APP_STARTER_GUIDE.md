# AGILANG Web App Starter Guide

This guide explains how developers should use AGILANG to create web applications with `.ags` reactive templates, authentication, password reset, and SMTP/email configuration.

> Branch note: this guide may be referenced from `main`, but the complete public web app starter kit should live on the `blog` branch.

## 1. Install AGILANG Runtime

Clone the repository and use the runtime branch:

```bash
git clone https://github.com/GLOBAL-FINTECH/agilang.git
cd agilang
git checkout main
python -m pip install -e .
agi --version
```

Expected result:

```text
AGILANG 1.9.3
```

## 2. Use the Web App Starter Branch

For the full web app starter kit, switch to the `blog` branch:

```bash
git checkout blog
```

The `blog` branch is where the public starter app should live. It can include blog/news pages, user dashboard, admin dashboard, authentication, password reset, SMTP settings, and `.ags` views.

## 3. Create a New Web App

Create a standard AGILANG web app:

```bash
agi new my-web-app
cd my-web-app
```

Run it locally:

```bash
agi serve src/main.agi --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## 4. Recommended Starter Structure

```text
my-web-app/
├─ agilang.toml
├─ .env.example
├─ .env
├─ src/
│  ├─ main.agi
│  ├─ config.agi
│  ├─ routes/
│  │  ├─ web.agi
│  │  └─ api.agi
│  ├─ controllers/
│  ├─ services/
│  └─ middleware/
├─ resources/
│  ├─ views/
│  │  ├─ layout.ags
│  │  ├─ home.ags
│  │  ├─ login.ags
│  │  ├─ register.ags
│  │  ├─ forgot-password.ags
│  │  ├─ reset-password.ags
│  │  ├─ dashboard.ags
│  │  └─ admin.ags
│  └─ assets/
│     ├─ css/app.css
│     └─ js/ags-runtime.js
├─ database/
│  └─ migrations/
├─ storage/
│  ├─ app.sqlite
│  └─ logs/
└─ tests/
```

## 5. Environment Configuration

Create `.env` from `.env.example`:

```env
APP_NAME="AGILANG Web App"
APP_ENV=local
APP_DEBUG=true
APP_URL=http://127.0.0.1:8000
APP_SECRET=change-this-secret-key

DATABASE_PATH=storage/app.sqlite

MAIL_MAILER=smtp
MAIL_HOST=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-smtp-password
MAIL_ENCRYPTION=tls
MAIL_FROM_ADDRESS=no-reply@example.com
MAIL_FROM_NAME="AGILANG Web App"

PASSWORD_RESET_TOKEN_MINUTES=60
```

Never commit real `.env` secrets. Commit only `.env.example`.

## 6. SMTP / Email Configuration

AGILANG web app starters should read SMTP values from environment variables.

| Key | Purpose |
|---|---|
| `MAIL_HOST` | SMTP server hostname |
| `MAIL_PORT` | Usually `587` for TLS or `465` for SSL |
| `MAIL_USERNAME` | SMTP username |
| `MAIL_PASSWORD` | SMTP password or app password |
| `MAIL_ENCRYPTION` | `tls`, `ssl`, or blank depending on provider |
| `MAIL_FROM_ADDRESS` | Sender email address |
| `MAIL_FROM_NAME` | Sender display name |

Example Gmail-style SMTP configuration:

```env
MAIL_HOST=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=yourname@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_ENCRYPTION=tls
MAIL_FROM_ADDRESS=yourname@gmail.com
MAIL_FROM_NAME="AGILANG App"
```

For production, use a transactional email provider such as Amazon SES, Mailgun, SendGrid, Postmark, or a verified company SMTP server.

## 7. Password Reset Flow

A production starter should include:

1. User opens `/forgot-password`.
2. User submits an email address.
3. System creates a secure random token.
4. System stores only the hashed token.
5. System emails a reset link.
6. User opens `/reset-password?email=...&token=...`.
7. User sets a new password.
8. System verifies token, expiry, and email.
9. System updates password hash.
10. System marks the token as used.

## 8. Password Reset Migration

```sql
create table if not exists password_resets (
  id integer primary key autoincrement,
  email text not null,
  token_hash text not null,
  expires_at text not null,
  used_at text,
  created_at text not null
);
```

## 9. Recommended Routes

Web routes:

```text
GET  /forgot-password
POST /forgot-password
GET  /reset-password
POST /reset-password
```

API routes:

```text
POST /api/auth/forgot-password
POST /api/auth/reset-password
```

## 10. Forgot Password Handler Pattern

```agi
fn forgot_password_action(request):
    let email = request.input("email", "").strip().lower()

    if email == "":
        return json_response({"ok": False, "error": "email_required"}, status=422)

    let user = db().one("select id, email, name from users where email = ?", [email])

    # Always return a neutral response so attackers cannot discover registered emails.
    if user == None:
        return json_response({"ok": True, "message": "If the account exists, a reset email has been sent."})

    let token = random_secure_token(64)
    let token_hash = hash_token(token)
    let expires_at = now_plus_minutes(int(os.environ.get("PASSWORD_RESET_TOKEN_MINUTES", "60")))

    db().execute(
        "insert into password_resets (email, token_hash, expires_at, created_at) values (?, ?, ?, ?)",
        [email, token_hash, expires_at, now()]
    )

    let reset_url = APP_URL + "/reset-password?email=" + url_encode(email) + "&token=" + url_encode(token)

    send_email(
        to=email,
        subject="Reset your password",
        body="Open this link to reset your password: " + reset_url
    )

    return json_response({"ok": True, "message": "If the account exists, a reset email has been sent."})
```

## 11. Reset Password Handler Pattern

```agi
fn reset_password_action(request):
    let email = request.input("email", "").strip().lower()
    let token = request.input("token", "")
    let password = request.input("password", "")
    let confirm = request.input("password_confirmation", "")

    if email == "" or token == "" or password == "":
        return json_response({"ok": False, "error": "missing_fields"}, status=422)

    if password != confirm:
        return json_response({"ok": False, "error": "passwords_do_not_match"}, status=422)

    if len(password) < 8:
        return json_response({"ok": False, "error": "password_too_short"}, status=422)

    let token_hash = hash_token(token)

    let reset = db().one(
        "select * from password_resets where email = ? and token_hash = ? and used_at is null order by id desc limit 1",
        [email, token_hash]
    )

    if reset == None:
        return json_response({"ok": False, "error": "invalid_or_expired_token"}, status=400)

    if reset["expires_at"] < now():
        return json_response({"ok": False, "error": "invalid_or_expired_token"}, status=400)

    let password_hash = hash_password(password)

    db().execute("update users set password_hash = ? where email = ?", [password_hash, email])
    db().execute("update password_resets set used_at = ? where id = ?", [now(), reset["id"]])

    return json_response({"ok": True, "message": "Password reset successful."})
```

## 12. Required Starter Pages

| Page | Purpose |
|---|---|
| `/` | Public landing page |
| `/login` | User login |
| `/register` | User registration |
| `/forgot-password` | Request password reset email |
| `/reset-password` | Set a new password |
| `/dashboard` | User dashboard |
| `/admin` | Admin dashboard, admin-only |
| `/profile` | User profile settings |

## 13. Admin/User Separation

Normal users must not see admin links.

Rules:

- Admin links render only when `current_user.role == "admin"`.
- `/admin` requires admin middleware.
- `/dashboard` is the normal user dashboard.
- Admin users may be redirected from `/dashboard` to `/admin`.
- User navigation and admin navigation must be separate.

## 14. Production Checklist

Before production:

- Set `APP_DEBUG=false`
- Use a strong `APP_SECRET`
- Configure real SMTP
- Use HTTPS
- Validate CSRF tokens
- Hash passwords securely
- Hash password reset tokens
- Expire reset tokens
- Rate-limit login and password reset
- Never reveal whether an email exists
- Protect `/admin` with role checks
- Back up the database
- Configure logs and monitoring
- Run the test suite

## 15. Run Tests

```bash
agi check src tests
agi run tests/test_main.agi
```

## 16. Developer Message

The `main` branch contains the AGILANG runtime. To build a full web application, use the `blog` branch starter kit:

```bash
git clone https://github.com/GLOBAL-FINTECH/agilang.git
cd agilang
git checkout blog
```
