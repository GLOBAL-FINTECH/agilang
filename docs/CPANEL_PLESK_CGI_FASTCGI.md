# AGILANG v1.4 cPanel / Plesk CGI + FastCGI Support

AGILANG v1.4 adds shared-hosting deployment support for environments where apps are loaded through Apache CGI/FastCGI rather than a long-running server process.

## What is supported

| Mode | Status | Notes |
|---|---:|---|
| Classic CGI | Supported | Requires only Python and executable `app.cgi`. |
| FastCGI | Supported when host exposes FastCGI/flup | Uses `app.fcgi`; falls back clearly if unavailable. |
| cPanel `public_html` | Supported | `agi new` and `agi hosting scaffold` generate `public_html/.htaccess`. |
| Plesk `httpdocs` | Supported | Copy generated `public_html/*` into `httpdocs/` or set document root. |
| Passenger / Setup Python App | Supported | Uses generated `passenger_wsgi.py`. |
| WebSockets on CGI | Not supported by CGI itself | Run realtime as a long-running AGILANG/native runtime process where allowed. |

## Create a new app

```bash
agi new test app two
cd test-app-two
agi run
agi serve src/main.agi --host 127.0.0.1 --port 8000
```

The generated project includes:

```text
public_html/.htaccess
public_html/app.cgi
public_html/app.fcgi
passenger_wsgi.py
deployment/CPANEL_PLESK_CGI_FASTCGI.md
```

## Add shared-hosting files to an existing app

```bash
agi hosting scaffold --mode auto --entry src/main.agi
```

## cPanel upload

1. Upload the project folder.
2. Ensure Python can import `agilang`.
3. Use `public_html/` as the domain document root.
4. Set executable permissions:

```bash
chmod 755 public_html/app.cgi public_html/app.fcgi
```

5. Open your domain.

## Plesk upload

Copy the contents of `public_html/` to `httpdocs/`, or set the document root to `public_html/`. If Plesk Python app mode is enabled, point it at `passenger_wsgi.py`.

## Diagnostics

```bash
agi hosting capabilities
agi hosting doctor
```

## How routing works

The generated `.htaccess` file uses Apache rewrite rules so requests are routed to `app.cgi`, similar to PHP front-controller setups like Laravel's `public/index.php`.

## Realtime note

Classic CGI and FastCGI are request/response execution models. They are not designed for persistent WebSocket connections. Use AGILANG's realtime server or native/hybrid runtime behind a reverse proxy when your host allows long-running processes.
