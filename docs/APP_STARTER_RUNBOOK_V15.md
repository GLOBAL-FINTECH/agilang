# AGILANG v1.5 App Starter Runbook

## Install AGILANG

```bash
python -m pip install -e .
agi --version
```

## Create a new full web app

AGILANG accepts multi-word names and converts them to a safe folder slug.

```bash
agi new test app two
cd test-app-two
```

Generated structure:

```text
test-app-two/
  agilang.toml
  src/main.agi
  src/realtime.agi
  templates/home.html
  templates/dashboard.html
  public/css/app.css
  public/js/app.js
  storage/.gitkeep
  tests/test_main.agi
  public_html/.htaccess
  public_html/app.cgi
  public_html/app.fcgi
  passenger_wsgi.py
  deployment/NGINX.md
  deployment/CADDY.md
  deployment/CPANEL_PLESK_CGI_FASTCGI.md
```

## Run the app

```bash
agi run
agi test
agi serve src/main.agi --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
agi run src/realtime.agi
```

## Generate React web and mobile clients

```bash
agi react web test-app-two-web
agi react mobile test-app-two-mobile
agi react sdk ./sdk
```

## Generate Android/iOS native bridge source

```bash
agi mobile native-bridge test-app-two-native --target both
```

## Verify runtime support

```bash
agi runtime platform-matrix
agi mobile platform-matrix
agi hosting capabilities
```
