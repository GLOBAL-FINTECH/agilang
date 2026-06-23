# AGILANG Social + Blog + News + 18+ Dating Suite

This starter demonstrates how AGILANG can power a full product family from one backend:

- Blog and news publishing with roles, drafts, review, and published stories.
- Facebook-style social feed using `/social` and `/api/social-feed`.
- TikTok-style short-video feed using `/videos` and `/api/video-feed`.
- Safety-first adult-only dating discovery using `/dating` and `/api/dating/suggestions`.

The branded names are used only as product-category references. The starter does not copy any proprietary platform UI, API, algorithm, or trademarked product behavior.

## Editable AGS files

```text
resources/views/social.ags
resources/views/videos.ags
resources/views/dating.ags
resources/views/posts.ags
resources/views/post.ags
resources/views/dashboard.ags
```

## Live data lifecycle

1. `.ags` files declare `@fetch` and `@live` for scalar data such as `{{ stats.social }}`.
2. `ags-runtime.js` hydrates `data-ags-live` scalar bindings without a full page refresh.
3. Repeating lists use `data-ags-repeat`, `data-ags-path`, and an HTML `<template>` block.
4. Backend JSON routes return safe, typed data dictionaries.

## Dating engine production requirements

The dating page is an architecture starter only. Before production, add:

- Strict 18+ age verification.
- Identity checks where legally required.
- Report, block, mute, and moderation queues.
- Abuse/spam detection.
- Privacy controls and data retention policy.
- Local legal compliance review.

No minor matching or explicit content should be supported.
