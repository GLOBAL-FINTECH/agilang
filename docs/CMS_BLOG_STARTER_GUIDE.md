# AGILANG CMS / Blog Starter Guide

This guide defines the professional CMS/blog starter for the `blog` branch.

## Goal

The starter should showcase AGILANG as a practical programming language and web framework, not as a static template.

Every visible CMS section should be connected to:

- a backend route,
- an API endpoint,
- a database query,
- a configuration file,
- seed/demo data,
- or a proper empty state.

## Core pages

| Page | Purpose |
|---|---|
| `/` | Public homepage |
| `/blog` | Blog/news listing |
| `/blog/<slug>` | Post detail page |
| `/categories/<slug>` | Category archive |
| `/login` | User/admin login |
| `/forgot-password` | Password reset request |
| `/reset-password` | Password reset form |
| `/dashboard` | User dashboard |
| `/admin` | Admin dashboard |
| `/admin/posts` | Manage posts |
| `/admin/pages` | Manage CMS pages |
| `/admin/media` | Manage uploads |
| `/admin/settings` | Site settings |

## Recommended database tables

```sql
create table if not exists users (
  id integer primary key autoincrement,
  name text not null,
  email text not null unique,
  password_hash text not null,
  role text not null default 'user',
  created_at text not null
);

create table if not exists posts (
  id integer primary key autoincrement,
  title text not null,
  slug text not null unique,
  excerpt text,
  body text not null,
  status text not null default 'draft',
  author_id integer,
  published_at text,
  created_at text not null
);

create table if not exists categories (
  id integer primary key autoincrement,
  name text not null,
  slug text not null unique
);

create table if not exists password_resets (
  id integer primary key autoincrement,
  email text not null,
  token_hash text not null,
  expires_at text not null,
  used_at text,
  created_at text not null
);
```

## Routes

```agi
fn register_web_routes(app):
    app.get("/", home_page)
    app.get("/blog", blog_index)
    app.get("/blog/<slug>", blog_show)
    app.get("/login", login_page)
    app.post("/login", login_action)
    app.get("/forgot-password", forgot_password_page)
    app.post("/forgot-password", forgot_password_action)
    app.get("/reset-password", reset_password_page)
    app.post("/reset-password", reset_password_action)
    app.get("/dashboard", user_dashboard)
    app.get("/admin", admin_dashboard)
```

## SMTP configuration

`.env`:

```env
MAIL_MAILER=smtp
MAIL_HOST=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-smtp-password
MAIL_ENCRYPTION=tls
MAIL_FROM_ADDRESS=no-reply@example.com
MAIL_FROM_NAME="AGILANG CMS"
```

## Password reset behavior

Use neutral responses so attackers cannot discover registered emails:

```agi
return json_response({"ok": True, "message": "If the account exists, a reset email has been sent."})
```

Store only token hashes, never raw reset tokens.

## Admin/user separation

Rules:

- Admin links render only for `role == "admin"`.
- `/admin` requires admin middleware.
- Normal users never see admin menu items.
- Admin dashboard and user dashboard must be separate.

## Empty states

If no posts exist, the blog page should show:

```text
No posts published yet.
```

Do not show fake static cards as if they are real posts.

## Production checklist

- `APP_DEBUG=false`
- strong `APP_SECRET`
- real SMTP configured
- HTTPS enabled
- password hashing enabled
- reset token hashing enabled
- reset token expiry enabled
- admin routes protected
- uploads validated
- database backed up
- logs configured
- tests passing
