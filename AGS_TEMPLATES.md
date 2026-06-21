# AGILANG AGS Templates

AGS means **AGILANG Reactive Template** or **AGILANG Single-file View**.

Use `.ags` files for editable pages and components that can carry page
metadata, SEO tags, and future live-data directives:

```text
resources/views/home.ags
resources/views/dashboard.ags
resources/views/components/stat-card.ags
```

## Page Metadata

```html
@page title="Pricing" seo_description="Pricing for this AGILANG app." robots="index,follow"
@layout "layout.ags"

<section class="dashboard">
  <h1>{{ title }}</h1>
</section>
```

`render_ags()` returns:

```text
body  - rendered HTML
meta  - parsed @page metadata
seo   - rendered SEO/Open Graph/Twitter tags
```

## SEO Helpers

Use `seo_tags()` in a layout:

```html
<title>{{ title }}</title>
{{{ seo }}}
```

Supported SEO fields:

```text
title
description
canonical
image
type
site_name
robots
locale
twitter_card
author
keywords
json_ld
```

## Live Data Directives

AGS reserves these directives for reactive pages:

```html
@fetch stats from "/api/home-stats"
@live stats from "/api/home-stats" every 5000
```

The current runtime parses these directives as metadata. The browser runtime in
`resources/assets/js/ags-runtime.js` can hydrate matching elements:

```html
<strong data-ags-fetch="/api/home-stats" data-ags-path="users">0</strong>
<strong data-ags-live="/api/home-stats" data-ags-path="items" data-ags-every="5000">0</strong>
```

## CLI

```powershell
agi make:page pricing
agi make:component stat-card
agi make:api home-stats
```

These commands generate files and print route guidance for `src/main.agi`.

## Recommended Structure

```text
resources/
  views/
    layout.ags
    home.ags
    dashboard.ags
    components/
      stat-card.ags
  assets/
    css/
      app.css
    js/
      ags-runtime.js
```


## AGS live data

See `docs/AGS_LIVE_DATA.md` for the full lifecycle of `@fetch`, `@live`, and automatic `{{ stats.users }}` browser binding.
