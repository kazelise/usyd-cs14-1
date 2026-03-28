# Architecture

## System Overview

```
┌───────────────────┐         ┌───────────────────────┐
│  Researcher        │         │  Participant           │
│  (Admin UI)        │         │  (Survey Page)         │
└────────┬──────────┘         └────────┬──────────────┘
         │                             │
         ▼                             ▼
┌──────────────────────────────────────────────────────┐
│  Frontend (Next.js + React + Tailwind)               │
│                                                      │
│  /admin/*              Survey editor    [Frontend A] │
│  /survey/[shareCode]   Participant feed [Frontend B] │
└────────────────────────┬─────────────────────────────┘
                         │  REST API (JSON)
┌────────────────────────▼─────────────────────────────┐
│  Backend (FastAPI)                                    │
│                                                      │
│  /api/v1/auth/*        Authentication    [Backend A] │
│  /api/v1/surveys/*     Survey + Post CRUD[Backend A/B]│
│  /api/v1/tracking/*    Gaze + Click      [Backend C] │
└────────┬─────────────────────────────────────────────┘
         │
    ┌────▼────┐
    │PostgreSQL│
    └──────────┘
```

## Data Flow: Complete Survey Session

```
Researcher Side:
1. Register + Login                    POST /auth/register, /auth/login
2. Create survey (set A/B groups)      POST /surveys
3. Add posts by URL (OG auto-fetch)    POST /surveys/{id}/posts
4. Override title, set fake likes etc  PATCH /surveys/{id}/posts/{pid}
5. Add fake comments to posts          POST /surveys/{id}/posts/{pid}/comments
6. Publish survey                      POST /surveys/{id}/publish → share_code

Participant Side:
7. Open share link → random group      POST /surveys/{share_code}/start
8. (Optional) Webcam calibration       POST /tracking/calibration/sessions
9. View posts, like/comment/click      POST /surveys/responses/{id}/interact
10. Gaze data sent in batches          POST /tracking/gaze
11. Click data sent in batches         POST /tracking/clicks
12. Complete survey                    POST /surveys/responses/{id}/complete

Researcher Side:
13. Export all data                    GET /surveys/{id}/export
```

## Database Tables (10 tables)

```
researchers              [Backend A]  — researcher accounts
surveys                  [Backend A]  — surveys with A/B group config
survey_posts             [Backend B]  — posts with OG metadata + fake numbers
post_comments            [Backend B]  — fake comments by researcher
survey_responses         [Backend A/B]— participant sessions + group assignment
participant_interactions [Backend A/B]— likes, comments, clicks by participant
calibration_sessions     [Backend C]  — webcam calibration sessions
calibration_points       [Backend C]  — calibration point data
gaze_records             [Backend C]  — continuous gaze XY stream
click_records            [Backend C]  — mouse click positions
```

## Key Design Decisions

**OG Metadata Fetching**: When researcher pastes a URL, backend fetches the HTML
and extracts `<meta property="og:title">`, `og:image`, `og:description`, `og:site_name`.
Same mechanism Facebook/Twitter uses for link previews. No API needed.

**A/B Testing**: Survey has `num_groups` (e.g., 2). Each post has `visible_to_groups`
(e.g., [1]) and `group_overrides` (e.g., {"1": {"display_likes": 1000}}). When
participant opens survey, they're randomly assigned to a group. Backend filters
posts accordingly.

**Tracking Data**: Gaze and click data is sent in batches (every 5-10 seconds)
to avoid flooding the backend. Each record has a `post_id` field so researchers
can analyze attention per post.

**Participant Interactions**: Likes, comments, and clicks on posts are stored in
`participant_interactions`, completely separate from the fake numbers set by
the researcher. This gives researchers two datasets: what was shown vs how
participants reacted.
