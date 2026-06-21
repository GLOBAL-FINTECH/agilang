# Deployment Guide

## Local Development

```bash
agilang serve src/main.agi --host 127.0.0.1 --port 8000
```

## VPS

```bash
agilang serve src/main.agi --host 0.0.0.0 --port 8000
```

Put Nginx or Caddy in front of it.

## Shared Hosting

Generate files:

```bash
agilang hosting scaffold --root . --entry src/main.agi --target public_html --mode auto
```

Upload:

```text
public_html/
vendor/agilang/
src/
resources/
storage/
```

Make `storage/` writable.
