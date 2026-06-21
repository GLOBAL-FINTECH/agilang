# Split-File Architecture

Do not place everything in `src/main.agi`. Split app logic into modules.

## Recommended Structure

```text
src/
├─ main.agi
├─ config.agi
├─ routes/
│  ├─ web.agi
│  └─ api.agi
├─ controllers/
│  ├─ HomeController.agi
│  └─ ApiController.agi
└─ services/
   ├─ StripeService.agi
   └─ PayPalService.agi
```

## main.agi

```agi
import "config.agi"
import "routes/web.agi"
import "routes/api.agi"

fn create_app():
    let app = web_app(APP_NAME, True)
    register_web_routes(app)
    register_api_routes(app)
    return app
```

## routes/web.agi

```agi
import "../controllers/HomeController.agi"

fn register_web_routes(app):
    app.get("/", home_page)
    app.get("/dashboard", dashboard_page)
```

## controllers/HomeController.agi

```agi
fn home_page(request):
    return page_response("../resources/views/home.ags", {"app_name": APP_NAME})
```
