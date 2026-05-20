# CS14 documentation index

Human-facing docs live in this directory. For deployment and live-demo scripts, start with [`deployment.md`](./deployment.md) and [`DEMO_RUNBOOK.md`](./DEMO_RUNBOOK.md). The repository root [`README.md`](../README.md) adds a condensed **Demo Showcase** table beside this index.

**Public demo smoke (no secrets):** [`scripts/verify_demo_public.sh`](../scripts/verify_demo_public.sh) — curls `/health` **and each published demo share code** (`CS14DEMO2026` + six gallery codes by default) for `en` + `zh`; override hosts, schemes (`DEMO_SCHEME`), or narrowed code lists via env vars spelled out in the script header.

| Document | Audience | Purpose |
| --- | --- | --- |
| [`DEMO_RUNBOOK.md`](./DEMO_RUNBOOK.md) | Presenters | ~20-minute client meeting script: URLs, timings, slide wording for gaze claims, export, camera fallback |
| [`deployment.md`](./deployment.md) | Operators | Prod host layout, `.env`, Caddy, Compose commands, HTTPS/CORS/smoke checklist |
| [`researcher-user-guide.md`](./researcher-user-guide.md) | Researchers | Building surveys, translations, publishing, export |
| [`CS14_ACCEPTANCE_CHECKLIST.md`](./CS14_ACCEPTANCE_CHECKLIST.md) | Team | Requirement vs implementation matrix |
| [`architecture.md`](./architecture.md) and docs-site Project pages | Engineers / client | Subsystem overview, frontend design, database design, API reference |
| [`tracking-api.md`](./tracking-api.md), [`tracking-data-flow.md`](./tracking-data-flow.md), [`tracking-design-decisions.md`](./tracking-design-decisions.md) | Engineers | Calibration/gaze API contracts and design rationale |

**VitePress site:** source under [`docs-site/docs/`](../docs-site/docs/). It is published at `https://cs14-docs.kazelis.top/`; run `cd docs-site && npm install && npm run dev` locally if you want a browsable sidebar.
