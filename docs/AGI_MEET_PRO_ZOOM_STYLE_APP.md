# AGI Meet Pro Zoom-Style App

AGI Meet Pro is a professional Zoom-style video meeting application built with the AGILANG framework, AGS templates, browser JavaScript, same-origin API realtime chat, and browser-native media APIs.

This document explains the app architecture, the professional UI structure, the camera and audio fix, and how to run and test the app.

---

## 1. Purpose

AGI Meet Pro demonstrates how an AGILANG web app can be organized like a Laravel-style application while still using AGILANG syntax and AGS templates.

It includes:

```text
professional meeting landing page
meeting dashboard
schedule meeting page
join meeting page
live meeting room
room chat
participants panel
notes panel
camera controls
microphone controls
audio meter
browser media diagnostics
same-origin realtime API polling
camera and microphone security policy fix
```

---

## 2. Laravel-style AGILANG structure

The app is organized using a professional controller/service/view layout:

```text
my-web-app/
  src/
    main.agi
    realtime.agi

  routes/
    web.agi
    api.agi

  app/
    controllers/
      HomeController.agi
      MeetingController.agi
      ApiController.agi
    services/
      MeetingService.agi
    middleware/
      SecurityMiddleware.agi
    framework/
      View.agi

  resources/
    views/
      layout.ags
      home.ags
      dashboard.ags
      schedule.ags
      join.ags
      meeting.ags
      camera_test.ags
      recordings.ags
    assets/
      css/app.css
      js/agilang-browser-bridge.js
      js/meeting-runtime.js
      js/ags-runtime.js

  public/
    css/app.css
    js/agilang-browser-bridge.js
    js/meeting-runtime.js

  storage/
    app.sqlite

  docs/
    ARCHITECTURE.md
    MEETING_RUNBOOK.md
    CAMERA_ERROR_AND_AUDIO_FIX.md
```

---

## 3. Main app flow

```text
browser request
  -> AGILANG web server on port 8000
  -> routes/web.agi or routes/api.agi
  -> controller
  -> service
  -> AGS template or JSON API response
  -> browser JavaScript runtime
```

The meeting room uses:

```text
GET  /meeting?room=agimeet-demo
GET  /api/messages?room=agimeet-demo
POST /api/messages
GET  /api/meeting?room=agimeet-demo
GET  /camera-test
```

---

## 4. Unified realtime design

The app now uses same-origin API realtime behavior instead of requiring a second terminal/server for chat.

Old model:

```text
web server:      localhost:8000
websocket server: localhost:9001
```

Current model:

```text
web server:      localhost:8000
chat API:        localhost:8000/api/messages
camera/audio:    browser getUserMedia through AGILANG Browser Bridge
```

This means the user can run one server:

```powershell
agi serve src/main.agi --host 127.0.0.1 --port 8000
```

and open:

```text
http://localhost:8000/meeting?room=agimeet-demo
```

---

## 5. Silent chat update fix

The early version refreshed the full chat panel every second. This worked but caused visible flashing.

The fixed behavior is:

```text
poll messages quietly
compare message fingerprint
skip DOM updates when nothing changed
append only new messages
preserve existing message cards
scroll only when needed
```

This makes chat feel like a professional realtime UI without flicker.

---

## 6. Camera root cause

The camera originally failed even though the browser and device were working. Chrome DevTools showed:

```text
[Violation] Permissions policy violation: camera is not allowed in this document.
```

That error means the browser received a server policy that blocked camera access before JavaScript could open the webcam.

The restrictive header looked like:

```text
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

The fixed header must allow same-origin camera and microphone:

```text
Permissions-Policy: camera=(self), microphone=(self), display-capture=(self), fullscreen=(self)
```

---

## 7. Content Security Policy fix

The browser also showed an inline script error:

```text
Executing inline script violates the Content Security Policy directive default-src 'self'
```

The fix was to remove inline JavaScript from `meeting.ags` and use HTML `data-*` attributes instead.

Example:

```html
<div id="meeting-app" data-room-id="agimeet-demo" data-join-url="/meeting?room=agimeet-demo"></div>
```

Then `meeting-runtime.js` reads the room value from the DOM instead of relying on inline script.

---

## 8. Camera and audio browser bridge

The app now uses an AGILANG browser bridge file:

```text
resources/assets/js/agilang-browser-bridge.js
public/js/agilang-browser-bridge.js
```

The bridge is responsible for browser-level media work:

```text
secure origin detection
permissions API checks
device enumeration
camera request
microphone request
video-only fallback
audio-only retry
error translation
audio meter support
```

Important: AGILANG can serve the app and define the framework, but only browser JavaScript can call:

```javascript
navigator.mediaDevices.getUserMedia({ video: true, audio: true })
```

The browser still controls final permission.

---

## 9. Camera-first, microphone-second flow

The fixed media flow avoids the old failure where microphone denial could prevent video from starting.

Current flow:

```text
1. Request video-only first.
2. Attach video stream to the local video tile.
3. Request microphone separately.
4. If microphone is denied, keep video running.
5. Let the Mic button retry audio later.
6. Show audio meter only when audio is live.
```

This is the correct browser media design for a professional meeting app.

---

## 10. Audio behavior

The microphone system now supports:

```text
Mic waiting
Mic ready
Mic live
Mic muted
Mic blocked
Mic disconnected
local audio meter
microphone retry
```

When the microphone is live, the audio meter moves when the user speaks.

---

## 11. Camera test page

The app includes a dedicated media diagnostics page:

```text
http://localhost:8000/camera-test
```

It should show:

```text
bridge version
secure origin status
camera permission state
microphone permission state
number of cameras detected
number of microphones detected
```

Use this page before testing the full meeting room.

---

## 12. Professional UI notes

The UI was upgraded to behave more like a professional meeting app:

```text
fixed app shell
left workspace navigation
meeting command bar
meeting info header
responsive meeting stage
gallery tiles
right-side chat/participants/notes panel
bottom meeting toolbar
professional dark theme
mobile/tablet layout fixes
```

On mobile-width screens, the layout stacks so the meeting stage and chat do not overlap.

---

## 13. Browser-extension warnings

Some Chrome console warnings came from extension content scripts, for example:

```text
contentscript.js
ObjectMultiplex
MaxListenersExceededWarning
```

Those are not AGI Meet app errors. They usually come from browser extensions such as wallets, dev tools, or monitoring extensions.

The important AGI Meet errors were:

```text
Permissions policy violation: camera is not allowed
Content Security Policy inline script blocked
WebSocket failed on same port
```

Those app-level issues were fixed.

---

## 14. Run commands

From the app folder:

```powershell
cd my-web-app
agi serve src/main.agi --host 127.0.0.1 --port 8000
```

Open:

```text
http://localhost:8000
http://localhost:8000/camera-test
http://localhost:8000/meeting?room=agimeet-demo
```

---

## 15. Validation commands

```powershell
PYTHONPATH=vendor python -m agilang.cli check src/main.agi
PYTHONPATH=vendor python -m agilang.cli run src/main.agi
PYTHONPATH=vendor python -m agilang.cli test
```

Expected result:

```text
OK: src/main.agi
AGI Meet dev check: {"ok":true,"app":"AGI Meet","runtime":"agilang","template":"zoom-style-meetings","status":"online"}
PASS tests/test_main.agi
```

---

## 16. Production gaps

This is a professional AGILANG meeting app foundation, but production video meetings still require:

```text
TURN server for NAT traversal
SFU/media server for group calls
user authentication
authorization and room access policies
recording storage
meeting audit logs
rate limiting
end-to-end media security review
production HTTPS deployment
```

---

## 17. Final status

The camera issue was caused by browser security headers, not by the webcam. The current fix works because the AGILANG app now sends media-safe security headers, avoids inline scripts, separates video from audio, and uses a dedicated AGILANG Browser Bridge for browser media operations.
