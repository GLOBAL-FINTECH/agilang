# Debugging and Error Handling

## Most Important Debug Commands

```bash
agilang check src tests
agilang run src/main.agi --check
agilang run src/main.agi --dump
agilang to-py src/main.agi --line-map
agilang tokens src/main.agi
agilang ast src/main.agi --pretty
agilang typecheck src tests
agilang doctor
```

## Invalid JSON or Broken Page Output

If a browser page shows something like:

```text
{'body': '...', 'meta': {...}}
```

The route is returning the full AGS render object. Return the body inside the layout instead.

Bad:

```agi
let view = render_ags("../resources/views/social.ags", {})
return html_response(view)
```

Good:

```agi
let view = render_ags("../resources/views/social.ags", {})
return html_response(render_template("../resources/views/layout.ags", {
    "title": view["meta"].get("title", "Social"),
    "seo": view["seo"],
    "body": view["body"]
}))
```

## Safe Page Helper

```agi
fn page_response(template, data):
    try:
        let view = render_ags(template, data)
        return html_response(render_template("../resources/views/layout.ags", {
            "title": view["meta"].get("title", "AGILANG"),
            "seo": view["seo"],
            "body": view["body"]
        }))
    except Exception as exc:
        return html_response("<h1>Page Error</h1><p>" + str(exc) + "</p>", status=500)
```

## API Error Pattern

```agi
fn api_example(request):
    try:
        return json_response({"ok": True})
    except Exception as exc:
        return json_response({"ok": False, "error": "api_failed", "message": str(exc)}, status=500)
```
