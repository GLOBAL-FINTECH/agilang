# AGI Meet Camera Error and Audio Fix

This document records the camera and audio issue found during AGI Meet browser testing and the fix that made the camera work.

---

## 1. Confirmed browser error

Chrome DevTools showed this error:

```text
[Violation] Permissions policy violation: camera is not allowed in this document.
```

This error means the browser blocked camera access because the page response included a restrictive `Permissions-Policy` header.

The issue was not the camera device itself.

---

## 2. Root cause

The AGILANG web app was using default security headers that blocked camera and microphone access.

A restrictive policy looks like this:

```text
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

When this header is present, Chrome blocks:

```javascript
navigator.mediaDevices.getUserMedia({ video: true })
```

before the JavaScript camera bridge can open the webcam.

---

## 3. Correct fixed policy

AGI Meet requires a meeting-safe policy:

```text
Permissions-Policy: camera=(self), microphone=(self), display-capture=(self), fullscreen=(self)
```

The app also needs a CSP that allows local scripts and media blobs:

```text
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self' ws: wss:; object-src 'none'; base-uri 'self'; frame-ancestors 'self'
```

---

## 4. Inline script issue

Chrome also showed:

```text
Executing inline script violates the Content Security Policy directive default-src 'self'
```

The fix is:

```text
Do not place inline JavaScript in meeting.ags.
Move runtime logic into public/js/meeting-runtime.js.
Pass server-side values using HTML data attributes.
```

Example:

```html
<section id="meeting-app" data-room-id="agimeet-demo" data-join-url="/meeting?room=agimeet-demo"></section>
```

Then JavaScript reads:

```javascript
const app = document.getElementById('meeting-app');
const roomId = app.dataset.roomId;
```

---

## 5. WebSocket same-port issue

Chrome also showed:

```text
WebSocket connection to 'ws://localhost:8000/realtime' failed
```

The fix was to use the same AGILANG web server for chat realtime via API polling:

```text
GET  /api/messages?room=agimeet-demo
POST /api/messages
```

The app can still add WebSocket later, but it should not try to connect to a non-existing same-port WebSocket endpoint by default.

---

## 6. Working media design

The final working camera/audio flow is:

```text
1. User clicks Start camera.
2. Browser bridge requests camera/video first.
3. App attaches the camera stream to the local video tile.
4. Browser bridge requests microphone/audio separately.
5. If audio fails, video remains active.
6. User can retry microphone from the Mic button.
7. Audio meter shows microphone input when available.
```

This avoids the browser failure mode where microphone denial blocks the entire camera request.

---

## 7. Files involved

```text
src/main.agi
app/middleware/SecurityMiddleware.agi
resources/views/meeting.ags
resources/views/camera_test.ags
resources/assets/js/agilang-browser-bridge.js
resources/assets/js/meeting-runtime.js
resources/assets/css/app.css
public/js/agilang-browser-bridge.js
public/js/meeting-runtime.js
public/css/app.css
```

---

## 8. Test pages

Run the app:

```powershell
agi serve src/main.agi --host 127.0.0.1 --port 8000
```

Open diagnostics:

```text
http://localhost:8000/camera-test
```

Open meeting:

```text
http://localhost:8000/meeting?room=agimeet-demo
```

---

## 9. Expected successful behavior

After the fix:

```text
Camera video appears in the local meeting tile.
Browser permission prompt appears when required.
The meeting page no longer reports camera disallowed by Permissions-Policy.
Chat continues to work through same-origin API realtime.
Microphone can be allowed, muted, retried, and measured with the audio meter.
```

---

## 10. What AGILANG can and cannot control

AGILANG can:

```text
serve the meeting app
define routes/controllers/services
send correct security headers
serve JavaScript bridge files
provide API realtime chat
provide AGS views
```

Browser JavaScript can:

```text
request camera permission
request microphone permission
attach MediaStream to video elements
show audio levels
handle permission errors
```

The browser controls:

```text
final camera permission
final microphone permission
Incognito permission behavior
Windows privacy enforcement
whether another app is already using the camera
```

No framework can bypass browser permission rules. The correct solution is to send the right headers, run on localhost or HTTPS, and request media through browser JavaScript.

---

## 11. Final result

The camera fix has been confirmed working in the browser. The webcam stream appears in the meeting tile after correcting the `Permissions-Policy` and CSP behavior.
