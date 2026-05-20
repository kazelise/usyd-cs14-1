# PDF/MVP Coverage Matrix

This matrix maps every listed PDF/MVP item from the CS14 acceptance checklist to current documentation coverage, expected product behavior, and final acceptance evidence.

| # | PDF/MVP item | Documentation coverage | Expected product behavior | Acceptance evidence |
|---:|---|---|---|---|
| 1 | Working deployed MVP | [Local Setup & Live Deployment](./setup-deployment.md) covers local smoke testing and the live Japan VM deployment. | Docker Compose runs PostgreSQL, FastAPI, Next.js, Caddy, and Cloudflare Tunnel; the public app is available at `https://cs14.kazelis.top/`. | Public `/health`, Swagger, frontend, seeded participant link, and docs site smoke checks pass. |
| 2 | Admin survey builder with create/edit surveys, blocks, and question types | [Researcher Workflow](../guide/researcher-workflow.md) documents create/edit, blocks, and question types. | Researcher can create surveys, add/edit/reorder content blocks, and configure free text, single choice, multiple choice, Likert, and rating questions. | Builder UI smoke test, persisted block changes, backend route tests, frontend build. |
| 3 | Social-media post template editor with feed posts, cards, counts, comments, source labels, and More Information buttons | [Researcher Workflow](../guide/researcher-workflow.md) and [Social Post Fetching](../guide/social-post-fetching.md) document the card editor and fetch/manual fallback rules. | Researcher can fetch metadata when possible, override all display fields, set engagement counts, write comment previews, and track More Information clicks. | Post card preview per condition/language, participant feed rendering, interaction tracking in export. |
| 4 | Preview/testing workflow | [Researcher Workflow](../guide/researcher-workflow.md) defines preview before publish and test-session discipline. | Researcher can preview selected condition/language without polluting final analytics, then perform a participant smoke run. | Preview session excluded or marked, condition/language rendering verified, share link copied only after review. |
| 5 | At least 2 languages end-to-end, translation CSV/JSON import/export, and participant language selection | [Data Export & Translations](../guide/data-export.md) gives explicit import/export and participant language-selection steps. | Admin exports translation templates, imports completed translations, and participant language choice drives rendered survey content. | CSV/JSON roundtrip, selected language stored on response, English/Chinese plus Arabic RTL checked where available. |
| 6 | Participant runner with clean UI, condition assignment, and randomisation | [Researcher Workflow](../guide/researcher-workflow.md) documents publish/share, participant run, and condition preview. | Participant opens one share link, chooses language, receives assigned condition, completes required blocks, and submits once. | Participant run smoke test, persisted response, condition assignment visible in analytics/export. |
| 7 | Camera calibration module with permission flow, guidance, face detection, dot sequence, score, and stored outcomes | [Calibration & Privacy](../guide/calibration-privacy.md) covers flow, troubleshooting, pass/fail interpretation, and privacy limits. | Participant grants camera permission, completes dot sequence, receives pass/acceptable/poor outcome, and calibration summary is stored without raw video. | Calibration session and points stored, numeric score/outcome exported, retry behavior checked. |
| 8 | Database schema for surveys, translations, anonymous participants, responses, calibration logs | [Data Export & Translations](../guide/data-export.md) and [Calibration & Privacy](../guide/calibration-privacy.md) document the researcher-visible data contract. | Data model supports surveys, posts, questions, translations, anonymous responses, interactions, calibration sessions, gaze/click summaries. | Alembic migrations, schema tests, privacy check that raw participant tokens/video are not exported. |
| 9 | CSV/JSON export with filters by survey, condition, and language | [Data Export & Translations](../guide/data-export.md) gives explicit CSV/JSON export and filter instructions. | Researcher exports owned survey data as CSV or JSON, filtered by survey, condition, language, completion status, calibration outcome, and preview inclusion. | Export files open cleanly, filters change row set, stable column/JSON schema, privacy exclusions verified. |
| 10 | Local and deployment setup docs plus researcher user guide | This VitePress site provides separate setup, deployment, researcher, export, fetching, calibration, and privacy pages. | A new team member can run locally, follow the researcher flow, understand live demo operations, and avoid unsupported fetch/export assumptions. | `npm run build` for docs, public docs at `https://cs14-docs.kazelis.top/`, and app smoke checklist before client demonstration. |

## Current Readiness Notes

- The docs site is intentionally separate from backend/frontend runtime code.
- Deployment instructions now describe the live Japan VM plus Cloudflare Tunnel setup.
- Product gaps should continue to be tracked in the main acceptance checklist and implementation issues.

## Live URLs

- Participant/researcher app: `https://cs14.kazelis.top/`
- Public docs site: `https://cs14-docs.kazelis.top/`
- Published participant smoke link: `https://cs14.kazelis.top/survey/CS14DEMO2026?lang=en`

## Client Feedback Status

| Feedback item | Current status | Handoff note |
|---|---|---|
| Platform UI dropdown for X, Facebook, Truth Social, Instagram, Bluesky | Partial | Current code carries platform UI style through survey create/edit and the participant renderer has distinct feed skins. Final review should verify one published survey per style because older branches collapsed Truth Social and Bluesky back to X-style. |
| External post/headline/image/More Information opens in a new tab | Done | Participant click handling opens `_blank` synchronously before interaction logging and keeps the survey tab on the same route. Browser QA should verify headline, image, and More Information each create one intentional `click` interaction. |
| Survey-time gaze/attention data | Partial | Calibration sessions and post-calibration gaze/click capture are implemented, including participant-token hardening and attention summary plumbing. Public browser evidence still needs a real camera or controlled fake-camera pass to confirm the live survey-time stream end to end. |
| Camera calibration flow | Done with device-risk | Webcam permission, face stability, dot sequence, score, and stored outcomes are implemented. Demo readiness still depends on HTTPS camera permission and room lighting on the presenter device. |
| CSV/JSON export with useful filters | Partial | Backend/export paths expose CSV and JSON filters for group/language/status/calibration/preview. Final acceptance should verify that the visible analytics/export UI changes row sets and labels export-only filters honestly. |
| Live deployment and docs links | Done | App and docs are live at the URLs above; do not revert wording to "deployment postponed". |

## Transcript Handoff Notes

- 8:17-13:52: client asked which platform UI is shown and requested a researcher dropdown for Facebook/X/Truth Social/Instagram/Bluesky-style presentation.
- 14:28-15:26: client said post clicks, including More Information, must open a separate tab so the participant does not lose the survey page.
- 16:04-17:33: client asked to see CSV/export data.
- 17:33-18:24: client asked where survey-time eye-tracking data is, not only calibration output.
- 18:24 onward: client asked to put these comments into the status check form and send the platform/Cloudflare links.

## External Click QA Checklist

- Start from the published participant smoke link above. If calibration blocks automation, complete calibration manually or use a local app run with a post that includes a hero image.
- Click the post headline, hero image, and More Information button separately.
- Expected result for each click: a separate tab opens to the original URL, the survey tab remains on `/survey/...`, and exactly one semantic `click` interaction is sent with the current `participant_token`.
- Expected raw click tracking: headline clicks are labelled `headline`, image clicks are labelled `image`, More Information clicks are labelled `more_info`, and action buttons keep their own labels.
