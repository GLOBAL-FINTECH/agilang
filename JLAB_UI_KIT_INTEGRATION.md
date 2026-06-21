# JLab UI Kit Integration for AGILANG Social Network Suite v2.3

This build maps the uploaded JLab social UI kit into the AGILANG social, blog, news, short-video, and adult-only dating discovery suite. The goal is to provide a production-oriented working app shell where each major UI section is connected to AGILANG routes, AGS templates, database tables, and JSON APIs.

## Integrated sections

| Section | Route | Backend/API wiring | Notes |
|---|---:|---|---|
| News portal | `/news` | Published `posts` filtered as news | Admin can disable `module_news`. |
| Blog magazine | `/blog` | Published `posts` filtered as blog/tutorial content | Admin can disable `module_blog`. |
| Facebook-style social feed | `/social` | `/api/social-feed`, `/api/social/posts`, `/api/social/people`, follows, likes, friend requests | Supports composer, media preview, profile sidebar, people discovery, and direct messaging panel. |
| TikTok-style short video | `/videos` | `/api/video-feed`, `/api/videos` | Supports uploaded/recorded video data URLs and reel-style cards. |
| 18+ dating discovery | `/dating` | `/api/dating/suggestions`, `/api/dating/profile`, `/api/dating/verification`, `/api/dating/like/<id>` | Adult-only profile gate plus admin-approved verification before discovery. |
| Admin control center | `/admin` | `app_settings`, reports, verification queue, media assets, audit logs | Admin controls modules, moderation reports, 18+ verification, media pipeline, and audit trail. |
| Direct messaging | `/api/social/messages` | `chat_messages` table | Supports text, image/video attachments, and audio/voice message data URLs. |
| Reports and blocking | `/api/reports`, `/api/admin/reports`, `/api/social/block/<id>` | `content_reports`, `blocked_users` tables | User UI creates reports/blocks; admin review can resolve, dismiss, or remove content. |
| Route catalog | `/routes`, `/api/routes` | `route_catalog()` | Lists app routes and usage purpose. |

## Admin feature toggles

The admin panel uses the `app_settings` table. These settings are seeded automatically during migration:

```text
module_news
module_blog
module_social
module_videos
module_dating
module_messaging
module_friend_requests
module_media_uploads
module_voice_messages
module_reports
module_monetization
module_age_verification
module_rate_limits
module_audit_logs
module_realtime
module_video_processing
module_cdn_storage
```

Disabled modules return a controlled `403` page instead of exposing an inactive UI. API endpoints also check the relevant module setting and return a JSON error such as `module_social_disabled`, `module_videos_disabled`, or `media_uploads_disabled`.

## UI files mapped from the kit

```text
resources/views/layout.ags                    Global JLab shell/topbar
resources/views/partials/nav_user.ags         Authenticated navigation
resources/views/partials/nav_guest.ags        Guest navigation
resources/views/social.ags                    Social network workspace
resources/views/videos.ags                    Short-video creator feed
resources/views/dating.ags                    18+ discovery workspace
resources/views/posts.ags                     Blog/news magazine listing
resources/views/admin.ags                     Admin dashboard and toggles
resources/views/components/setting_toggle.ags Admin settings row
resources/assets/css/app.css                  Base app CSS + JLab integration CSS
resources/assets/js/ags-runtime.js            Live AGS hydration/runtime handlers
```

## Live runtime behavior

The AGS runtime now hydrates these UI areas:

- `data-ags-repeat="/api/social-feed"` renders social posts.
- `data-ag-social-post` sends new social posts with optional image/video media.
- `data-ag-people` renders people cards and follow/friend-request buttons.
- `data-ag-chat-form` sends text, file-media, or voice/audio messages.
- `data-ags-repeat="/api/video-feed"` renders reel-style video cards.
- `data-ag-video-form` uploads creator videos.
- `data-ag-dating-form` saves adult-only dating profiles.
- `data-ag-form="dating-verification"` submits 18+ verification for admin approval.
- `data-ag-dating-list` renders dating discovery cards.
- `data-ag-action="report"` creates moderation reports through `/api/reports`.
- `data-ag-action="block"` creates user blocks through `/api/social/block/<id>`.
- Theme, mobile menu, tab, and reel-action controls are wired in `ags-runtime.js`.
- Admin report and verification rows post directly to `/admin/.../status` routes.

## Validation

Run the suite from the app root:

```powershell
$env:PYTHONPATH=".\docs"
python -m agilang run tests\test_main.agi
```

Linux/macOS equivalent:

```bash
PYTHONPATH=docs python -m agilang run tests/test_main.agi
```

The integrated test suite validates registration, session flow, dashboard, social posting, feed hydration APIs, people discovery, follow actions, direct messaging, video upload/feed, 18+ dating profile/suggestions, admin settings, report/block endpoints, and page rendering for social, video, and dating modules.

## v2.3 production-control status

Implemented in this package:

1. Durable local media storage under `storage/media`, exposed through `/media`.
2. Server-side media type and file-size limits.
3. Report queue with admin review, dismissal, resolution, and content-removal actions.
4. 18+ verification request and admin approval queue for dating discovery.
5. Rate limits for high-risk write actions.
6. Audit logs for user/admin safety actions.
7. Realtime event stream for WebSocket/SSE adapters.
8. Video-processing status hooks.
9. User notifications.

Still recommended before a large public launch: external object storage/CDN, malware scanning, transcoding workers, advanced spam/abuse detection, formal privacy/data-retention policies, and country-specific legal review.

