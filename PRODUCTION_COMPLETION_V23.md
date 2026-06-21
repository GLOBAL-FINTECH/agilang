# AGILANG v2.3 Production Completion Pass

This upgrade adds the remaining production-control layer requested for the AGILANG Social Network Suite. The app is still intentionally framework-light AGILANG, but the sections are no longer only visual starters: the admin and user workflows now write to real tables and guarded APIs.

## Added production modules

| Area | What now works | Main files/routes |
|---|---|---|
| Durable media storage | Image, video, audio/voice, avatar, cover, thumbnail, and dating-photo data URLs are validated, decoded, stored under `storage/media`, and returned as `/media/...` URLs. | `media_assets`, `/api/media/upload`, `/api/media/policy` |
| File-size/type limits | Server-side media validation rejects invalid MIME classes and oversized uploads. | `MEDIA_MAX_*` env vars, `validate_media_payload()` |
| Moderation workflow | Reports can be reviewed, resolved, dismissed, or used to remove social posts, short videos, and dating profiles. | `content_reports`, `/api/admin/reports`, `/admin/reports/<id>/status` |
| Audit logs | Important social, messaging, media, video, dating, verification, settings, and moderation actions are recorded. | `audit_logs`, Admin Audit Log table |
| Rate limits | Posts, videos, media uploads, messages, reports, and verification submissions are throttled per user/window. | `rate_limits`, `rate_limit_ok()` |
| Realtime bridge | User/admin actions write to `realtime_events`; clients can poll `/api/realtime/events` or bridge it into AGILANG WebSocket runtime. | `realtime_events`, `/api/realtime/events` |
| Notifications | Users receive stored notifications for follows, messages, and verification review outcomes. | `notifications`, `/api/notifications` |
| 18+ verification | Dating profiles are hidden from discovery until approved by admin verification. | `age_verifications`, `/api/dating/verification`, `/api/admin/age-verifications` |
| Video processing hooks | Uploaded videos can start as `queued`, then a worker/admin route marks them `ready`. | `short_videos.processing_status`, `/api/admin/videos/<id>/process` |
| Admin feature settings | Admin can enable/disable core modules plus age verification, rate limits, audit logs, realtime events, video processing, and CDN mode. | `app_settings`, `/admin/settings` |

## New user-facing workflow

1. User registers/signs in.
2. User can create social posts, upload media, follow people, send friend requests, send messages, upload videos, and submit reports.
3. Media is stored durably instead of remaining only as transient data URLs.
4. Dating users must submit an 18+ verification request.
5. Dating profile creation is allowed, but discovery shows only profiles with approved verification status.

## New admin workflow

Admin users can open `/admin` and manage:

- Module availability settings.
- Open report queue and content takedowns.
- 18+ verification approvals/rejections.
- Stored media table.
- Audit log table.
- Production pipeline status cards.

## Environment variables

```env
MEDIA_STORAGE_MODE=local
MEDIA_BASE_URL=/media
MEDIA_MAX_IMAGE_BYTES=2097152
MEDIA_MAX_VIDEO_BYTES=15728640
MEDIA_MAX_AUDIO_BYTES=3145728
MEDIA_MAX_AVATAR_BYTES=1048576
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_POSTS_PER_WINDOW=12
RATE_LIMIT_MESSAGES_PER_WINDOW=60
RATE_LIMIT_REPORTS_PER_WINDOW=20
```

## Important production notes

This v2.3 build implements the app-side hooks and working local pipelines. For a real public deployment, connect these hooks to external services where appropriate:

- Object storage/CDN such as S3, R2, MinIO, or another private media backend.
- Malware scanning and content-safety scanning workers.
- FFmpeg/transcoding workers for long video processing.
- WebSocket/SSE server for live chat/presence instead of polling only.
- Country-specific legal review for dating, privacy, age verification, and data retention.

## Validation

Run:

```bash
PYTHONPATH=docs python -m agilang run tests/test_main.agi
```

Expected result:

```text
AGILANG social network suite tests passed
```
