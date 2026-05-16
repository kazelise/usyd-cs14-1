# Demo runbook — CS14 public showcase

Use this alongside the README **Demo Showcase** section. It gathers examiner-facing URLs, seeded share codes, export talk-track wording, disposable credentials policy, and what data is **not** stored. The scripted **20‑minute meeting walkthrough** is still at the bottom of this file.

---

## Canonical URLs

| What | URL |
|------|-----|
| App (researcher admin + participant entry) | <https://cs14.kazelis.top/> |
| Participant surveys | `https://cs14.kazelis.top/survey/<SHARE_CODE>` (often via `/start` for consent/calibration) |
| Public documentation site | <https://cs14-docs.kazelis.top/> |
| Swagger / OpenAPI | <https://cs14.kazelis.top/docs> |

---

## Disposable demo researcher account

Use a **researcher** login only (never a participant vault). Holds **demo / synthetic surveys only** — it **may be reset** between rehearsals or deployments.

Maintainers **must keep this aligned** with whoever seeds production: configure `DEMO_RESEARCHER_EMAIL` / `DEMO_RESEARCHER_PASSWORD` env vars **before** `python -m scripts.seed_client_demo`, or edit this table + README together whenever the seeded identity changes after a DB wipe.

For the **staging host** seeded by the COMP5703 team:

| Field | Value |
|-------|-------|
| Sign-in URL | `https://cs14.kazelis.top/auth` |
| Email | `cs14.showcase.demo@example.com` |
| Password | `Cs14-Demo-Showcase-2026` |

Seed defaults (`cs14.demo@example.com` / `change-me-client-demo`) are only for unattended local smoke runs — swap them via env vars for any shared environment.

---

## Seeded datasets (canonical `seed_client_demo`)

Rebuild anytime from `backend/` (or backend container):

```bash
python -m scripts.seed_client_demo
```

The seed is **idempotent** on fixed share codes below: wipes and recreates each demo survey each run.

| Survey | Posts | Calibration / gaze demo | Groups |
|--------|-------|---------------------------|--------|
| **Main walkthrough** `CS14DEMO2026` | **six** stimulus cards (`MAIN_SURVEY_POST_CAP`), each with Likert engagement | ✅ Full calibration + seeded responses + gaze/click/comments | **`Control`** / **`High engagement cues`** (`group_names` in seed) |
| **Gallery** `CS14X2026`, `CS14IG2026`, `CS14RED2026`, `CS14TRUTH26`, `CS14BSKY2026`, `CS14DOUYIN26` | **four** curated cards each (`GALLERY_POST_CAP`) | ❌ Presentation-only previews (tracking off per survey shell) | Same labels for consistency |

Stimulus URLs embed **controlled copy** (`*.example`, lab vignettes, or stable CDN-free summaries) — demo runs avoid live Open Graph fetches that could fail mid-talk.

Translations: Chinese strings are seeded per post/question; Arabic remains in **`supported_languages`** for RTL layout checks even when copy is thinner than Chinese.

---

## Main walkthrough + platform gallery links

**Primary examiner path** — calibration → scroll → interactions → researcher analytics/export:

| Role | Purpose | Share code | Link |
|------|---------|------------|------|
| **Main walkthrough** | Default credibility-study storyline | **CS14DEMO2026** | <https://cs14.kazelis.top/survey/CS14DEMO2026> |

**Platform style gallery** — same codebase, tuned layouts:

| Share code | What to say | Participant link |
|------------|-------------|-------------------|
| **CS14X2026** | X-style **timeline** | <https://cs14.kazelis.top/survey/CS14X2026> |
| **CS14IG2026** | **Instagram-like** grid | <https://cs14.kazelis.top/survey/CS14IG2026> |
| **CS14RED2026** | **Xiaohongshu / RED** collage | <https://cs14.kazelis.top/survey/CS14RED2026> |
| **CS14TRUTH26** | Truth Social–motif column | <https://cs14.kazelis.top/survey/CS14TRUTH26> |
| **CS14BSKY2026** | Bluesky-style column | <https://cs14.kazelis.top/survey/CS14BSKY2026> |
| **CS14DOUYIN26** | Douyin/TikTok **vertical feed** | <https://cs14.kazelis.top/survey/CS14DOUYIN26> |

Add `?lang=en`, `?lang=zh`, or `?lang=ar` to force participant locale previews.

Opening a participant link assigns a synthetic session automatically—no standalone “participant login”.

---

## Quick reference (paste into meeting chat)

| What | Link / value |
| --- | --- |
| Public demo URL (researcher + participant) | `https://cs14.kazelis.top/` |
| API base / Swagger | `https://cs14.kazelis.top/docs` |
| Public docs site | `https://cs14-docs.kazelis.top/` |
| Participant deep link (EN) | `https://cs14.kazelis.top/survey/CS14DEMO2026?lang=en` |
| Participant deep link (中文) | `https://cs14.kazelis.top/survey/CS14DEMO2026?lang=zh` |
| Participant RTL smoke (ar) | `https://cs14.kazelis.top/survey/CS14DEMO2026?lang=ar` |
| Project docs index | [`docs/README.md`](./README.md); deeper guides: [`researcher-user-guide.md`](./researcher-user-guide.md), [`deployment.md`](./deployment.md), tracking docs |
| Repo demo seed | [`backend/scripts/seed_client_demo.py`](../backend/scripts/seed_client_demo.py) |

---

## Automated smoke checks (no credentials)

`scripts/verify_demo_public.sh` curls `/health` plus each published survey for **both** English and simplified Chinese payloads.

Defaults include **all seven** seeded share codes (`CS14DEMO2026` plus the six gallery codes). Override comma-free lists via `DEMO_SHARE_CODES`:

```bash
DEMO_HOST='cs14.kazelis.top' ./scripts/verify_demo_public.sh

# Local stack / plain HTTP smoke
DEMO_HOST='localhost:8000' DEMO_SCHEME='http' ./scripts/verify_demo_public.sh

# Narrow check
DEMO_SHARE_CODES='CS14DEMO2026' DEMO_HOST='cs14.kazelis.top' ./scripts/verify_demo_public.sh
```

---

## What to say — data & privacy (short script)

1. **“We simulate feeds for experiments.”** Engagement numbers/comments are scripted. Participants never see unpublished studies.

2. **“Attention evidence is behavioural—not a recording vault.”** MediaPipe-derived gaze/coordinates arrive from the webcam stream. **Raw video/JPEG snapshots are not stored.**

3. **“Calibration gates quality.”** Nine-point prompts produce `overall_quality` (`good` / `acceptable` / `poor`) from detection rate & sample depth before analytics ingest trust.

4. **“Exports are aggregates plus row-level behavioural traces.”** Admin **Analytics → Export Summary** emits JSON KPIs (`calibration_success_rate`, group splits, clicks/likes/comments/shares). Row dumps correspond to Postgres tables summarized below and [`tracking-data-flow.md`](./tracking-data-flow.md).

---

## Export surfaces in this codebase

| Surface | Format | Audience |
|---------|--------|----------|
| **Admin Analytics → Export Summary** | JSON (`survey`, `summary`, `exported_at`) — see [`frontend/app/admin/analytics/page.tsx`](../frontend/app/admin/analytics/page.tsx) | Quick deck / examiner walkthrough |
| **Full survey export** | CSV/JSON via `GET /surveys/{id}/export` (when enabled on branch) plus table-level dumps documented for thesis work |

Key summary fields surfaced today:

- `calibration_success_rate`
- Participant counts plus interaction totals **per experimental group**
- Post-level aggregates (clicks/likes/comments/shares/participant chatter)

---

## Field dictionary — where calibration, gaze, clicks, engagement live

High-level Postgres mapping — **privacy: no persisted video**.

### `survey_responses`

| Column / concept | Meaning |
|------------------|---------|
| `assigned_group` | Random A/B group index |
| `language` | Browser locale |
| `status` | `in_progress`, `completed`, `flagged`, etc. |
| `user_agent`, `screen_*` | Device context |
| `participant_fingerprint` | Salted duplicate-detection hash (**not** raw PII) |

### `calibration_sessions` + `calibration_points`

Face detection rate, per-point iris samples (**numeric only**).

### `gaze_records`

Timestamped XY gaze estimates + iris features tied to foreground `post_id`.

### `click_records`

`target_element` captures semantic hotspots (`like_button`, `headline`, …).

### `participant_interactions` & participant comments

Distinct tables for scripted likes/comments vs participant-authored chatter.

Interpret “attention confidence” as engineering trust—not clinical diagnosis.

---

## Sanity checklist before presenting

1. Load app + docs on eduroam/mobile hotspot once.
2. Disposable researcher login → verify each share-code survey exists server-side if you changed prod data.
3. Incognito **`CS14DEMO2026`** → jog through calibration sandbox once.
4. Run `./scripts/verify_demo_public.sh` from your laptop (~30 seconds).
5. Download analytics/export JSON locally in case corp browsers block blobs.

---

## 20‑minute scripted walkthrough

Use these timings verbatim where helpful; deepen translation/analytics discussions if stakeholders ask.

### Before the meeting (5 min)

- Chrome/Edge; pre-grant camera for `https://cs14.kazelis.top`.
- Sign in disposable researcher JWT **before** the call.
- Participant path: secondary window/incognito preserves “fresh participant” illusion.
- Optional backup JSON export if network flaky.

Minute **0‑2 framing:** Multilingual simulated feeds + optional webcam gaze—not clinical eye trackers.

Minute **2‑8 researcher:** Admin Surveys → show six-card deck, bilingual fields, **`Control` vs `High engagement cues` overrides**, gaze interval (1 Hz demo default), translations panel, publish state (**never flash `.env` / API secrets**).

Minute **8‑14 participant:** Open share link HTTPS → toggle `zh/ar` briefly → calibration story → interact with feed + Likert.

Minute **14‑18 data-out:** Analytics dashboard + export artefacts (explain anonymised IDs, calibration gating columns).

Minute **18‑20 Q&A:** Highlight privacy ledger, indicative gaze accuracy, OG fetch caveat (seed sidesteps bots), leaked participant-token rate-limit risk acceptable for seminar recruitment only.

<details>
<summary>Camera troubleshooting cheatsheet</summary>

| Symptom | Mitigation |
| --- | --- |
| No HTTPS/camera prompt | Confirm `https://`, reset site permission, retry incognito. |
| OS camera blocked | Re-enable privacy settings for browser. |
| Face detection red | Improve lighting/camera distance—call it expected variance. |
| Calibration `poor` | Narrate as QA signal; surveys can gate completion. |

</details>

### Quick validation curls

```bash
curl -sf https://cs14.kazelis.top/health
curl -sf "https://cs14.kazelis.top/api/v1/surveys/public/CS14DEMO2026?language=zh" | head -c 200
curl -sf "https://cs14.kazelis.top/api/v1/surveys/public/CS14BSKY2026?language=en" | head -c 120
```

## Slide-wording guardrails

- ✅ “Basic webcam gaze with nine-point calibration gating.”
- ✅ “Indicative fixation patterns for comparative analysis.”
- ❌ Avoid “clinical grade”, “sub-degree certainty”, “biometric identification”.

## Related docs

- [`tracking-data-flow.md`](./tracking-data-flow.md)
- [`tracking-api.md`](./tracking-api.md)
- [`architecture.md`](./architecture.md)
