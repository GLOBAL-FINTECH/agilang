# AGILANG v1.3 App Starter Runbook

AGILANG v1.3 adds a web-first project generator. The short command is `agi`, and the long command is `agilang`; both point to the same CLI.

## Create a new app

Single-word app name:

```bash
agi new test-app-one
```

Multi-word app name:

```bash
agi new test app two
```

The multi-word command creates a safe project folder:

```text
test-app-two/
```

## Generated files

The default `web` template generates:

```text
test-app-two/
  agilang.toml
  .env.example
  .gitignore
  src/main.agi
  src/realtime.agi
  templates/home.html
  templates/dashboard.html
  public/css/app.css
  public/js/app.js
  storage/.gitkeep
  tests/test_main.agi
  deployment/NGINX.md
  deployment/CADDY.md
  README.md
```

## Run the application

```bash
cd test-app-two
agi run
agi serve src/main.agi --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Run realtime WebSocket transport

Open a second terminal:

```bash
cd test-app-two
agi run src/realtime.agi
```

Then visit:

```text
http://127.0.0.1:8000/dashboard
```

## Test the app

```bash
agi test
agi check src tests
agi runtime platform-matrix
agi runtime doctor
```

## Template options

Full web starter, the default:

```bash
agi new my app
```

API starter:

```bash
agi new my api --template api
```

Minimal starter:

```bash
agi new my cli --template basic
```

## Native runtime checks

```bash
agi runtime platform-matrix
agi runtime prebuilt-status
agi runtime install-prebuilt
agi runtime doctor
```

`platform-matrix` is the fastest way to verify Windows, macOS, and Linux runtime support metadata.
