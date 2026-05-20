# API Reference

All routes are under `/api/v1`. Researcher endpoints require a bearer token. Public participant endpoints use a response-scoped `participant_token` after `start`.

## Auth

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/auth/register` | Create a researcher account. |
| `POST` | `/auth/login` | Return a JWT for admin operations. |
| `GET` | `/auth/me` | Read current researcher profile. |
| `PATCH` | `/auth/me` | Update researcher display name. |

## Survey Management

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/surveys` | Create a survey with platform style, group count, tracking, calibration, and language settings. |
| `GET` | `/surveys` | List researcher-owned surveys. |
| `GET` | `/surveys/{survey_id}` | Read one survey and its configuration. |
| `PATCH` | `/surveys/{survey_id}` | Update title, settings, status-adjacent fields, style, groups, and tracking flags. |
| `DELETE` | `/surveys/{survey_id}` | Delete a survey and dependent data. |
| `POST` | `/surveys/{survey_id}/publish` | Publish a draft and expose its share code. |
| `GET` | `/surveys/{survey_id}/preview` | Return the participant payload for a selected group/language without creating final export data. |

## Posts, Comments, Questions

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/surveys/{survey_id}/posts` | Create a post card from a URL and Open Graph metadata. |
| `GET` | `/surveys/{survey_id}/posts` | List post cards for editing. |
| `PATCH` | `/surveys/{survey_id}/posts/{post_id}` | Update display overrides, engagement numbers, group visibility, and labels. |
| `DELETE` | `/surveys/{survey_id}/posts/{post_id}` | Remove a post card. |
| `POST` | `/surveys/{survey_id}/posts/{post_id}/comments` | Add a researcher-authored fake comment. |
| `POST` | `/surveys/{survey_id}/posts/{post_id}/questions` | Add a post-attached question. |
| `GET` | `/surveys/{survey_id}/posts/{post_id}/questions` | List post-attached questions. |
| `PATCH` | `/surveys/{survey_id}/posts/{post_id}/questions/{question_id}` | Update question text/type/config/order. |
| `DELETE` | `/surveys/{survey_id}/posts/{post_id}/questions/{question_id}` | Delete a post-attached question. |
| `POST` | `/surveys/{survey_id}/questions` | Add a survey-level question. |
| `GET` | `/surveys/{survey_id}/questions` | List survey-level questions. |
| `PATCH` | `/surveys/{survey_id}/questions/{question_id}` | Update a survey-level question. |
| `DELETE` | `/surveys/{survey_id}/questions/{question_id}` | Delete a survey-level question. |

## Translations

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/surveys/{survey_id}/translations/export` | Export translation templates or completed translations as JSON/CSV. |
| `POST` | `/surveys/{survey_id}/translations/import` | Import JSON/CSV translations for survey, post, and question copy. |

## Participant Flow

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/surveys/public/{share_code}` | Read public landing metadata for a published survey. |
| `POST` | `/surveys/{share_code}/start` | Create or resume an anonymous participant response, assign group, and return posts/questions/tracking settings. |
| `GET` | `/surveys/responses/{response_id}/state` | Resume like/comment state with a valid participant token. |
| `POST` | `/surveys/responses/{response_id}/interact` | Record participant like/comment/share-style events. |
| `POST` | `/surveys/responses/{response_id}/likes/toggle` | Toggle current like state and record the event. |
| `POST` | `/surveys/responses/{response_id}/comments` | Create a participant-authored comment. |
| `PATCH` | `/surveys/responses/{response_id}/comments/{comment_id}` | Edit a participant-authored comment. |
| `DELETE` | `/surveys/responses/{response_id}/comments/{comment_id}` | Delete a participant-authored comment. |
| `POST` | `/surveys/responses/{response_id}/attention-summary` | Store survey-time face/eye coverage counts and server-computed confidence before completion. |
| `POST` | `/surveys/responses/{response_id}/complete` | Complete the response and persist final attention quality if supplied. |

## Tracking

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/tracking/calibration/sessions` | Start a calibration session for one response. |
| `POST` | `/tracking/calibration/sessions/{session_id}/points` | Store numeric samples for one calibration point. |
| `POST` | `/tracking/calibration/sessions/{session_id}/complete` | Compute pass/fail, quality score, and calibration summary. |
| `POST` | `/tracking/gaze` | Store batched survey-time gaze samples. |
| `POST` | `/tracking/clicks` | Store batched survey-time click samples. |

## Analytics and Export

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/surveys/{survey_id}/analytics-summary` | Return dashboard metrics, group comparison, engagement totals, and attention/export readiness. |
| `GET` | `/surveys/{survey_id}/participant-comments` | Return participant comments for qualitative review. |
| `GET` | `/surveys/{survey_id}/engagement-stats` | Return post/group engagement stats. |
| `GET` | `/surveys/{survey_id}/export?format=csv|json` | Export responses, answers, interactions, calibration, gaze, clicks, and confidence fields. |
