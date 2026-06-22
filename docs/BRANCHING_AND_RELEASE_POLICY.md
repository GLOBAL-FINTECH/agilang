# AGILANG Branching and Release Policy

Repository: `GLOBAL-FINTECH/agilang`

## Branch Roles

| Branch | Purpose | Public Use |
|---|---|---|
| `main` | Stable AGILANG runtime branch | Runtime, CLI, parser, AGS engine, blockchain/runtime modules, standard library, runtime docs, and tests. |
| `dev` | Runtime/framework development branch | Active development before promotion to `main`. |
| `blog` | Public web app starter branch | Blog/news/social starter, `.ags` templates, authentication, password reset, SMTP/email setup, admin/user dashboards, and starter docs. |

## Main Branch Rule

The `main` branch must remain focused on AGILANG runtime code. It should not become the full public-facing web application branch.

Allowed in `main`:

- AGILANG runtime source
- CLI commands such as `agi` and `agilang`
- parser/checker/formatter/runtime bridge
- AGS renderer/runtime support
- standard library modules
- blockchain/runtime modules
- runtime tests
- runtime installation documentation
- links to starter branches

Not allowed in `main`:

- full web starter app as the root app
- public social app as the root app
- demo databases
- uploaded media
- production user content
- admin/user dashboards that belong to starter applications

## Blog Branch Rule

The `blog` branch is the public AGILANG web application starter branch.

It should include:

- `.ags` web pages by default
- blog/news starter modules
- user dashboard
- admin dashboard
- login/register
- forgot password and reset password flows
- SMTP/email configuration
- database migrations
- deployment notes
- production checklist

## Recommended Development Flow

Runtime work:

```bash
git checkout dev
git pull origin dev
# make runtime changes
git add .
git commit -m "runtime: describe change"
git push origin dev
```

Promote runtime changes:

```bash
git checkout main
git pull origin main
git merge dev
git push origin main
```

Starter work:

```bash
git checkout blog
git pull origin blog
# make starter changes
git add .
git commit -m "starter: describe change"
git push origin blog
```

## GitHub Landing Page

If the repository landing page should show the public web app starter documentation, switch the GitHub default branch to `blog`:

```text
GitHub → Repository → Settings → Branches → Default branch → blog
```

If the default branch remains `main`, the README on `main` should remain runtime-focused and link developers to the `blog` branch.

## Final Rule

`main` = runtime only.  
`dev` = runtime development.  
`blog` = public web app starter.
