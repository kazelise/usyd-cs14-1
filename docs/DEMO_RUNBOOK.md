# 20-minute client demo runbook

Use this script for the live walkthrough of CS14 (researcher build → participant run → export), aligned with the parent MVP acceptance criteria. Adjust timings if the client wants more depth on translation or analytics.

## Quick reference (paste into the meeting chat)

| What | Link / value |
| --- | --- |
| Public demo URL (researcher + participant) | `https://cs14.kazelis.top/` |
| API base / Swagger | `https://cs14.kazelis.top/docs` |
| Public docs site | `https://cs14-docs.kazelis.top/` |
| Pre-seeded participant share link (EN) | `https://cs14.kazelis.top/survey/CS14DEMO2026?lang=en` |
| Pre-seeded participant share link (中文) | `https://cs14.kazelis.top/survey/CS14DEMO2026?lang=zh` |
| Pre-seeded participant share link (ar, RTL sanity) | `https://cs14.kazelis.top/survey/CS14DEMO2026?lang=ar` |
| Researcher demo account | Communicated out-of-band — see the KAZ-1 issue thread on Multica. Do not paste it into committed docs or external chats. |
| Project docs (in repo) | [`docs/README.md`](./README.md) for the full index; this file plus [`researcher-user-guide.md`](./researcher-user-guide.md), [`deployment.md`](./deployment.md), [`tracking-*.md`](./tracking-api.md) |
| Docs site (VitePress source) | `docs-site/docs/` — published at `https://cs14-docs.kazelis.top/`; run `cd docs-site && npm install && npm run dev` to preview locally |

## Live demo survey (stage host)

The **CS14 Client Demo - Social Media Credibility Study** (`share_code` `CS14DEMO2026`) on the public demo is the canonical clean seed: two social-style posts, post-attached Likert questions, **Control / High engagement cues** groups, **EN + 中文 + Arabic entry** content, seeded calibration/attention/export data, and platform gallery companion surveys.

### If the canonical survey is missing (fresh database or new host)

Use this checklist instead of improvising on stage (~15 minutes once). Credentials stay out-of-band per [`deployment.md`](./deployment.md).

1. **Sign in** as the demo researcher (or register a throwaway lab account on that environment only).
2. **Admin → Surveys → New survey**: give it a clear title (e.g. “Deployment smoke survey”), pick the social platform style you want to demo, and enable **webcam calibration** + **gaze tracking** at the rate you plan to cite (1 Hz matches the current script).
3. **Participant groups**: configure **at least two groups** (name them *Control* and *Treatment* so the analytics slide reads cleanly). Participants draw one group at random when they open the share link.
4. **Posts**: add **one** social-style post (paste any article URL or fill overrides manually). Attach **one inline question** — a Likert on trust or credibility matches the spoken demo.
5. **Translations**: open the translations UI for that survey and fill **Chinese** strings for the survey title, the post headline/body fields you surface, and the question text so `?lang=zh` is visibly different from English. Arabic copy can stay minimal if you only need RTL layout (`?lang=ar`).
6. **Publish** and copy the new **share link**. Update this runbook’s quick-reference table and any slides if the `share_code` changed.
7. **Verify without credentials** from your laptop:

   ```bash
   DEMO_HOST='cs14.kazelis.top' ./scripts/verify_demo_public.sh
   ```

   Defaults to the coordination staging host if `DEMO_HOST` is unset. The script checks `/health` and the public survey JSON for both `en` and `zh`.

To rebuild the clean demo dataset, run `python -m scripts.seed_client_demo` from the backend container or backend working directory with production environment variables loaded. The script recreates fixed demo share codes and does not write demo credentials into docs.

## Before the meeting (5 min)

- **Browser:** Desktop Chrome or Edge; grant camera permissions for `https://cs14.kazelis.top` in advance. Reading the camera prompt on stage burns ~30 seconds.
- **Researcher account:** Sign in once *before* the call so the JWT is fresh — login takes a noticeable round-trip on first hit. Use the demo account from the out-of-band reference; do not register a new account on stage.
- **Survey:** The seeded survey **CS14 Client Demo - Social Media Credibility Study** (share code `CS14DEMO2026`) is already published with two social-media-style posts, Likert questions, two groups (Control / High engagement cues), Chinese translations, seeded analytics, and attention-confidence data. If you want to demo creation from scratch, allow an extra ~5 min and skip Minute 8–14 below.
- **Second path:** Open the participant share link in a **private/incognito** window (or a second browser profile) so the flow looks like a fresh participant and the researcher session stays open in the original window.
- **Backup:** Keep a CSV/JSON export from a previous successful run in case the network fails mid-demo. Save it locally before the call.
- **Sanity-check the host:** Two quick commands you can run from the laptop ~10 minutes before the call:

  ```bash
  curl -sf https://cs14.kazelis.top/health        # → {"status":"ok"}
  curl -sf "https://cs14.kazelis.top/api/v1/surveys/public/CS14DEMO2026?language=zh" | head -c 200
  ```

  The second one should print Chinese text in the `title` field — that proves the multilingual content path is live.

## Minute 0–2 — Framing

One sentence: a social-feed survey platform with optional **basic webcam-based gaze / attention estimation** and multilingual (EN / 中文 / العربية) support, deployed end-to-end over HTTPS.

State on the slide and verbally:

> "Gaze and attention here are **basic webcam-based estimation with a 9-point calibration quality check** — useful for relative comparisons across a session, but **not high-accuracy clinical eye tracking**. We report calibration quality (face-detection rate, stability) alongside every response so researchers can filter unreliable sessions."

## Minute 2–8 — Researcher workflow

1. Sign in → **Admin → Surveys**. Show that the demo survey already exists; click into it.
2. Show **survey configuration**: title, description, platform style, two groups (Control / Treatment), calibration enabled, gaze tracking enabled at 1 Hz.
3. Show one **post** (URL override + custom title/source/comments/like counts) and the **inline question** (Likert: "How trustworthy does this post feel?").
4. Open the **translations** panel — show the second language fields filled in for Chinese. Mention CSV/JSON bulk import/export endpoints for scale.
5. **Publish state** + copy the **share link**. Do **not** display the API key or `.env` values on screen.

## Participant session token (FYI — not scripted on stage)

After the participant starts the survey, browser calls authenticate with an anonymous `participant_token` (issued with `response_id` on session start). The runner stores it transparently — you do **not** need to show it unless someone is debugging REST calls. Automated checks: omitting the token yields **422**; a wrong token gets **404** (same shape as unknown `response_id`, so IDs are not enumerable). Researchers already use JWTs on admin routes — unchanged.

## Minute 8–14 — Participant workflow

1. In incognito, open `https://cs14.kazelis.top/survey/CS14DEMO2026?lang=en` — that's HTTPS, so camera permissions will be offered.
2. Consent + **language** switch — toggle to `zh` to show the post title and question render in Chinese (proves the two-language path end to end).
3. **Webcam calibration**: grant camera permission, show the face-detection presence check, run the 9-point dot sequence, point at the resulting **quality score** (good / acceptable / poor).
4. Scroll the **feed**, like / comment / share at least one post, answer the Likert question, complete the session.
5. Mention that the participant token is cached client-side: closing and reopening the tab resumes the same response and skips calibration if it already passed.

## Minute 14–18 — Data out

1. Switch back to the researcher window → **Admin → Analytics:** completion rate, calibration pass rate, A/B-broken-down likes / comments / clicks, suspicious-session flags.
2. **Export** → CSV and JSON, with filters (group, language, calibration outcome, completion). Briefly open the file to show the anonymised participant ID column and the calibration-quality / tracking-summary columns. Raw session tokens never leave the database.

## Minute 18–20 — Q&A and known caveats

Wording you can re-use:

- **Privacy:** no raw video or images are stored; only aggregate calibration scores and time-series gaze samples are persisted, all keyed by an anonymous per-session ID derived from the participant token. See [`tracking-design-decisions.md`](./tracking-design-decisions.md).
- **Gaze accuracy:** indicative only; calibration quality is reported with every response so unreliable runs can be filtered out at analysis time.
- **Arabic RTL** UI is flagged in the README as awaiting native-speaker review for tone; the layout flip itself works at first paint.
- **OG fetch failures** depend on the tracking target article (some publishers block bots). The researcher composer always allows manual overrides.
- **Participant tracking flood:** token binding stops impersonation, but a *leaked* participant token could still batch-insert gaze/clicks until that session completes — acceptable for a closed demo; add server-side rate limits before open recruitment (see parent MVP issue risk list).
- The public custom domain uses Cloudflare Tunnel on standard HTTPS. Direct Caddy HTTPS on **`:8443`** remains only as a legacy fallback because port `443` on this VM is occupied by an unrelated `sing-box` service; this is intentional and documented in [`deployment.md`](./deployment.md).

## Camera troubleshooting / fallback

If a participant can't get the camera working in the live demo, fall back gracefully — don't try to debug on stage:

| Symptom | Action |
| --- | --- |
| Browser never prompts for camera | Check the URL is `https://cs14.kazelis.top`, not `http://`; check the site permission in the address bar (click the lock icon); try a fresh incognito window. |
| Camera prompt blocked at OS level | Open System Settings → Privacy → Camera and re-enable the browser. Then refresh the participant tab. |
| Face-detection check stays red | Improve lighting; make sure the laptop camera isn't covered; move closer; the demo room's overhead lights are often enough. |
| Calibration quality returns "poor" | This is a feature, not a failure — say so on stage. Show the score, mention the survey can either block or warn based on its threshold. |
| Hard failure mid-demo | Skip calibration: complete the session as if calibration were disabled, then point at a previously captured export to show the data path still works. |

## Quick validation commands (technical)

```bash
# basic health
curl -sf https://cs14.kazelis.top/health
# → {"status":"ok"}

# survey API reachable, multilingual content
curl -sf "https://cs14.kazelis.top/api/v1/surveys/public/CS14DEMO2026?language=en" | head -c 200
curl -sf "https://cs14.kazelis.top/api/v1/surveys/public/CS14DEMO2026?language=zh" | head -c 200
```

For full operational detail, see [`deployment.md`](./deployment.md) and [`researcher-user-guide.md`](./researcher-user-guide.md).

## Slide-wording cheatsheet

Use these phrasings on the deck or when scripting talk-track — they keep claims defensible:

- ✅ "Basic webcam-based gaze and attention estimation with a 9-point calibration quality check."
- ✅ "Calibration outcome (good / acceptable / poor) is stored alongside every response."
- ✅ "Indicative gaze and attention data for relative comparison within and across sessions."
- ❌ Avoid: "high-accuracy eye tracking", "clinical-grade", "sub-degree accuracy", "predicts user intent", "biometric identification".
