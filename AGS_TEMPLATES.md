# AGS Reactive Templates

AGS files are AGILANG Single-file View templates.

## Page Template

```ags
@page title="Home" seo_description="Home page."
@layout "layout.ags"
@fetch stats from "/api/home-stats"
@live stats from "/api/home-stats" every 5000

<section>
  <h1>{{ app_name }}</h1>
  <p>Users: {{ stats.users }}</p>
</section>
```

## Layout Template

```ags
<!doctype html>
<html>
<head>
  <title>{{ title }}</title>
  {{{ seo }}}
  <script src="/assets/js/ags-runtime.js" defer></script>
</head>
<body>
  {{{ body }}}
</body>
</html>
```

## Render From Backend

```agi
fn home(request):
    let view = render_ags("../resources/views/home.ags", {"app_name": "My App"})
    return html_response(render_template("../resources/views/layout.ags", {
        "title": view["meta"].get("title", "My App"),
        "seo": view["seo"],
        "body": view["body"]
    }))
```

## Escaping

Escaped output:

```ags
{{ user.name }}
```

Raw trusted HTML:

```ags
{{{ body }}}
```
