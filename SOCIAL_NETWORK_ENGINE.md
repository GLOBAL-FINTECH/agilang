# AGILANG Social Network Engine Starter

This starter now provides a usable baseline social network, short-video feed, and adult-only discovery module using AGS reactive templates.

## Pages

- `resources/views/social.ags` — profile editor, avatar/cover upload, post composer, photo/video capture, people discovery, follow/friend request actions, and direct messages.
- `resources/views/videos.ags` — short-video upload, device recording, preview, and live video feed.
- `resources/views/dating.ags` — 18+ safety-first discovery profile and match cards.

## APIs

- `GET /api/social/profile`
- `PUT /api/social/profile`
- `GET /api/social-feed`
- `POST /api/social/posts`
- `POST /api/social/posts/<id>/like`
- `GET /api/social/people`
- `POST /api/social/follow/<id>`
- `POST /api/social/friend-request/<id>`
- `GET /api/social/messages?user_id=<id>`
- `POST /api/social/messages`
- `GET /api/video-feed`
- `POST /api/videos`
- `GET /api/dating/suggestions`
- `PUT /api/dating/profile`
- `POST /api/dating/like/<id>`

## Device media capture

`resources/assets/js/ags-runtime.js` supports:

- Image upload using `<input type="file" accept="image/*">`
- Camera capture through `navigator.mediaDevices.getUserMedia()`
- Video upload using `<input type="file" accept="video/*">`
- Short recording through `MediaRecorder`
- Data URL previews and submission through JSON APIs

This is a zero-dependency starter implementation. Production systems should move large media into object storage such as S3-compatible storage, Cloudflare R2, local protected storage, or a CDN-backed media service.

## Safety and production requirements

Before production social/dating use, add:

- Media virus/malware scanning
- Abuse reporting and blocking flows
- Moderation queues and audit logs
- Rate limiting and anti-spam controls
- Identity/age verification where legally required
- Terms, privacy policy, and local legal review
- Object storage for uploaded media instead of database data URLs

The dating module is strictly adult-only discovery architecture. It does not include minor matching or explicit content.
