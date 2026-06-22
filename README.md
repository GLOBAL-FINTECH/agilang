# AGILANG CMS / Blog Starter Kit

> **Branch purpose:** the `blog` branch is the public-facing AGILANG web/CMS starter branch. The `main` branch remains the AGILANG programming language runtime, CLI, parser/runtime tooling, and blockchain runtime branch.

This branch showcases how AGILANG can be used to build a real web application with `.agi` source files, `.ags` templates, database-backed pages, authentication, password reset, SMTP/email configuration, admin content management, and deployment-ready structure.

**License:** MIT  
**Developed by:** Izukanji Sirwimba, AGILab, Izurex Center Place Limited

---

## What this starter demonstrates

| Area | Included concept |
|---|---|
| AGILANG language | `.agi` routes, controllers, services, helpers, app entrypoint |
| AGS templates | `.ags` layouts, pages, reusable UI sections, live data bindings |
| CMS/blog | posts, pages, categories, media, publishing workflow |
| Admin dashboard | content management, settings, users, reports |
| Authentication | login, registration, current-user helpers, protected routes |
| Password reset | reset tokens, email links, expiry, safe responses |
| Email/SMTP | `.env` configuration for transactional email |
| Deployment | local dev server, VPS, shared hosting notes |
| Documentation | starter guide, CMS guide, AGILANG showcase guide |

---

## Quick start

Install AGILANG from the runtime branch first:

```bash
git clone https://github.com/GLOBAL-FINTECH/agilang.git
cd agilang
python -m pip install -e .
```

Switch to the CMS/blog starter branch:

```bash
git checkout blog
```

Run the starter:

```bash
agi serve src/main.agi --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

---

## Recommended starter structure

```text
cms-starter/
├─ agilang.toml
├─ .env.example
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
│  │  ├─ blog.ags
│  │  ├─ post.ags
│  │  ├─ admin-dashboard.ags
│  │  ├─ login.ags
│  │  ├─ forgot-password.ags
│  │  └─ reset-password.ags
│  └─ assets/
├─ database/migrations/
├─ storage/
├─ public_html/
└─ tests/
```

---

## Environment and SMTP setup

Create `.env` from `.env.example`:

```env
APP_NAME="AGILANG CMS Starter"
APP_ENV=local
APP_DEBUG=true
APP_URL=http://127.0.0.1:8000
APP_SECRET=change-this-secret

DATABASE_PATH=storage/app.sqlite

MAIL_MAILER=smtp
MAIL_HOST=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-smtp-password
MAIL_ENCRYPTION=tls
MAIL_FROM_ADDRESS=no-reply@example.com
MAIL_FROM_NAME="AGILANG CMS"

PASSWORD_RESET_TOKEN_MINUTES=60
```

Never commit real `.env` credentials.

---

## Password reset workflow

The starter should support:

```text
GET  /forgot-password
POST /forgot-password
GET  /reset-password
POST /reset-password
```

Safe password reset behavior:

1. User enters email.
2. App creates secure token.
3. App stores hashed token.
4. App emails reset link through SMTP.
5. User sets new password.
6. App validates token, expiry, and password confirmation.
7. App updates password hash and marks token used.

Full guide:

```text
docs/CMS_BLOG_STARTER_GUIDE.md
```

---

## AGS example

```ags
@page title="Blog" seo_description="AGILANG CMS blog page."
@layout "layout.ags"
@fetch posts from "/api/posts"

<section class="blog-grid">
  <h1>{{ title }}</h1>
  <div data-repeat="posts">
    <article>
      <h2>{{ item.title }}</h2>
      <p>{{ item.excerpt }}</p>
      <a href="/blog/{{ item.slug }}">Read more</a>
    </article>
  </div>
</section>
```

Backend API:

```agi
fn api_posts(request):
    let posts = db().query("select title, slug, excerpt from posts where status = ? order by published_at desc", ["published"])
    return json_response({"posts": posts})
```

---

## Documentation

| Document | Purpose |
|---|---|
| `docs/WEB_APP_STARTER_GUIDE.md` | Web app starter instructions |
| `docs/CMS_BLOG_STARTER_GUIDE.md` | CMS/blog app structure, routes, password reset, SMTP |
| `docs/AGILANG_WEB_SHOWCASE.md` | How this branch showcases the language |
| `docs/BRANCHING_AND_RELEASE_POLICY.md` | Branch separation policy |

---

## Branch relationship

| Branch | Purpose |
|---|---|
| `main` | AGILANG runtime, language docs, CLI, blockchain runtime |
| `blog` | CMS/blog/web starter kit and public application showcase |
| `dev` | Active framework/runtime development |
| `evm-chain-implementations` | EVM chain implementation track |

---

## Starter quality rule

No page should be a fake static template. Every visible section must be backed by a route, config, database query, seed/demo data file, or a proper empty state.
