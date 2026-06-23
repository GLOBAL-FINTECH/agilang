# AGS Live Data Lifecycle

AGS is the default AGILANG reactive view format. Use `.ags` files for pages and components instead of hardcoded HTML strings.

## 1. Declare data on the page

```html
@fetch stats from "/api/home-stats"
@live stats from "/api/home-stats" every 5000

<strong>{{ stats.users }}</strong>
<strong>{{ stats.items }}</strong>
<strong>{{ stats.status }}</strong>
```

## 2. Backend returns JSON

```agilang
fn api_home_stats(request):
    return json_response({"users": 10, "items": 25, "status": "online"})
```

## 3. Server renders the first page

`render_ags()` reads the directives, keeps the HTML editable, and converts `{{ stats.users }}` into safe browser bindings. Developers no longer need to manually write `data-ags-live` attributes.

## 4. Browser hydrates the bindings

`resources/assets/js/ags-runtime.js` fetches the declared endpoint and updates the bound text nodes without a full page refresh.

## 5. Polling and realtime modes

- `@fetch` loads data once.
- `@live ... every 5000` refreshes data on an interval.
- WebSocket-backed live directives can be added for transaction streams, chat, POS events, blockchain height, and WebRTC signaling status.

## File locations

- Homepage: `resources/views/index.ags`
- Home demo: `resources/views/home.ags`
- Dashboard: `resources/views/dashboard.ags`
- Layout: `resources/views/layout.ags`
- Components: `resources/views/components/*.ags`
- Client runtime: `resources/assets/js/ags-runtime.js`
- Backend routes: `src/main.agi`
