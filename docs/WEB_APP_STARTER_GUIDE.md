# AGILANG Web App Starter Guide

This branch is the public AGILANG web app starter branch. It is intended for developers who want to build blog, news, social, admin dashboard, and business web applications using AGILANG and `.ags` reactive templates.

## 1. Branch Purpose

| Branch | Purpose |
|---|---|
| `main` | AGILANG runtime only: CLI, parser, AGS engine, standard library, blockchain/runtime modules, runtime docs, and tests. |
| `dev` | Runtime/framework development branch. |
| `blog` | Public web app starter branch with `.ags` views, authentication, password reset, SMTP/email setup, admin/user dashboards, and deployable starter documentation. |

## 2. Install Runtime

```bash
git clone https://github.com/GLOBAL-FINTECH/agilang.git
cd agilang
git checkout main
python -m pip install -e .
agi --version
```

## 3. Use This Starter Branch

```bash
git checkout blog
```

Run the app:

```bash
agi serve src/main.agi --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## 4. Recommended Web App Structure

```text
agilang-web-starter/
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
│  │  ├─ admin.ags
│  │  ├─ blog.ags
│  │  └─ profile.ags
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

## 5. `.env.example`

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

Never commit a real `.env` file with production secrets.

## 6. SMTP / Email Setup

| Key | Purpose |
|---|---|
| `MAIL_HOST` | SMTP host name. |
| `MAIL_PORT` | Usually `587` for TLS or `465` for SSL. |
| `MAIL_USERNAME` | SMTP username. |
| `MAIL_PASSWORD` | SMTP password or provider app password. |
| `MAIL_ENCRYPTION` | `tls`, `ssl`, or blank depending on provider. |
| `MAIL_FROM_ADDRESS` | Sender email address. |
| `MAIL_FROM_NAME` | Sender display name. |

Example:

```env
MAIL_HOST=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=yourname@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_ENCRYPTION=tls
MAIL_FROM_ADDRESS=yourname@gmail.com
MAIL_FROM_NAME="AGILANG App"
```

For production, use a verified transactional email provider or company SMTP server.

## 7. Password Reset Requirements

A complete web app starter should support:

- `/forgot-password`
- `/reset-password`
- secure random reset tokens
- hashed token storage
- token expiry
- token single-use marking
- neutral response so attackers cannot discover registered emails
- email delivery through configured SMTP
- rate limiting on reset requests

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

```text
GET  /
GET  /login
POST /login
GET  /register
POST /register
GET  /forgot-password
POST /forgot-password
GET  /reset-password
POST /reset-password
GET  /dashboard
GET  /admin
GET  /profile
```

API routes:

```text
POST /api/auth/forgot-password
POST /api/auth/reset-password
GET  /api/me
GET  /api/posts
POST /api/posts
```

## 10. Admin/User Separation

The starter must separate admin and user navigation.

Rules:

- Normal users must not see admin links.
- `/admin` must require admin middleware.
- `/dashboard` is the standard user dashboard.
- Admin users may be redirected from `/dashboard` to `/admin`.
- Admin and user menus must be rendered separately.

## 11. Required Pages

| Page | Purpose |
|---|---|
| `/` | Public landing page. |
| `/login` | User login. |
| `/register` | User registration. |
| `/forgot-password` | Request a password reset email. |
| `/reset-password` | Create a new password. |
| `/dashboard` | User dashboard. |
| `/admin` | Admin-only dashboard. |
| `/profile` | User profile/settings page. |
| `/blog` | Blog/news listing. |

## 12. Production Checklist

Before deployment:

- Set `APP_DEBUG=false`.
- Use a strong `APP_SECRET`.
- Configure real SMTP.
- Use HTTPS.
- Validate CSRF tokens.
- Hash passwords securely.
- Hash password reset tokens.
- Expire reset tokens.
- Rate-limit login and reset endpoints.
- Never reveal whether an email exists.
- Protect `/admin` with role checks.
- Back up the database.
- Configure logs and monitoring.
- Run tests.

## 13. Test Commands

```bash
agi check src tests
agi run tests/test_main.agi
```

## 14. Development Rule

Keep the full web app starter in `blog`. Keep the AGILANG runtime in `main`.
