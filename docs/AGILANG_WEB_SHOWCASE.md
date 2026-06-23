# AGILANG Web Showcase Guide

The `blog` branch should demonstrate how AGILANG works as a programming language and application framework.

## Showcase goals

The starter should show:

1. `.agi` backend source files.
2. `.ags` reactive templates.
3. web routes and API routes.
4. database-backed pages.
5. admin/user separation.
6. authentication and password reset.
7. SMTP email configuration.
8. clean empty states.
9. production-ready project structure.

## Language demonstration sections

Add documentation or example pages for:

| Feature | Example |
|---|---|
| Functions | route handlers and service functions |
| Structs | user/post/category models |
| Imports | split routes/controllers/services |
| Templates | `.ags` pages and layouts |
| Database | SQLite queries and migrations |
| APIs | `/api/posts`, `/api/settings`, `/api/profile` |
| Auth | login/current user/admin middleware |
| Email | password reset email through SMTP |

## Public homepage layout

Recommended homepage sections:

1. Hero: AGILANG CMS starter.
2. What AGILANG is.
3. Live blog/news section backed by `/api/posts`.
4. AGS template explanation.
5. CLI command cards.
6. Admin dashboard preview.
7. Deployment steps.
8. Link to GitHub documentation.

## Admin dashboard modules

The admin dashboard should include:

- posts
- pages
- categories
- media
- users
- settings
- email/SMTP status
- password reset logs or audit records

## Static-template rule

Do not show fake data as real application activity.

Allowed:

- clearly labeled demo seed data,
- empty states,
- generated examples in documentation,
- screenshots marked as examples.

Not allowed:

- fake posts appearing as public activity,
- fake user activity with no database source,
- admin links visible to normal users,
- static UI cards pretending to be backend-connected.

## Recommended message

Use this positioning:

> AGILANG is a programming language and modular application runtime for building web apps, APIs, CMS/blog platforms, business dashboards, realtime apps, and blockchain-enabled systems. This starter branch shows how to build a production-oriented CMS using `.agi` source files and `.ags` reactive templates.
