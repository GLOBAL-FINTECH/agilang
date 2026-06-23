# App Structure

## `src/main.agi`

This is the application entrypoint. It contains:

- Environment configuration
- SQLite connection and migrations
- Route handlers/controllers
- Auth/session helpers
- API endpoints
- View bridge functions that render templates from `resources/views`

## `resources/views`

This is where developers customize pages without touching business logic.

Recommended convention:

```text
resources/views/index.ags             public index page at /
resources/views/home.ags              reactive home page at /home
resources/views/evm.ags               reactive EVM RPC page
resources/views/about.ags              sample extra page
resources/views/auth.ags               shared login/register form
resources/views/dashboard.ags          signed-in dashboard
resources/views/profile.ags            profile editor
resources/views/security.ags           security page
resources/views/layout.ags             global HTML wrapper with SEO tags and AGS runtime
resources/views/partials/              navigation and shared partials
resources/views/components/            repeated UI blocks
```

## `resources/assets/css`

CSS is separated from AGILANG source code so users can customize design directly.

## `data`

SQLite files are runtime artifacts. The starter ships with `data/.gitkeep`, not a pre-filled database.

## `tests`

`tests/test_main.agi` launches the app, performs login/register/API checks, and uses `data/test.sqlite` to avoid polluting the development database.


## AGS live data

See `docs/AGS_LIVE_DATA.md` for the full lifecycle of `@fetch`, `@live`, and automatic `{{ stats.users }}` browser binding.
