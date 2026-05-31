# CI/CD pipeline

This document describes the CS14-1 continuous integration and delivery pipeline. It is the
final-delivery counterpart to the sample group's "Jenkins.tar.gz" and "Jenkins deploy guide"
items: **CS14-1 does not use Jenkins.** Our stack is built and validated with **GitHub
Actions** and shipped with **Docker Compose** behind **Caddy + Cloudflare Tunnel**. This page
records that real pipeline so the delivery checklist maps cleanly onto what we actually run.

For the production host layout (`docker-compose.prod.yml`, Caddyfile, `.env`) see
[`deployment.md`](./deployment.md). For a clean-checkout deployment walkthrough see
[`deployment-video-script.md`](./deployment-video-script.md).

---

## Why GitHub Actions instead of Jenkins

The sample delivery checklist (CS63-1) assumes a Jenkins server with archived job configs and
a Jenkins-specific deploy guide. We deliberately chose a different toolchain:

- **No standing CI server to maintain.** GitHub Actions runs on GitHub-hosted runners, so the
  team does not operate, patch, or pay for a Jenkins controller for a one-semester capstone.
- **Config lives in the repo.** The pipeline is a single version-controlled file,
  [`.github/workflows/ci.yml`](../.github/workflows/ci.yml), reviewed through the same PR
  process as application code — there is no separate Jenkins UI state to export or back up.
- **Native to our branch/PR model.** Checks run automatically on every pull request into
  `dev` and `main`, which is exactly where our review gate sits (see Branch model below).

The deliverable equivalent of "Jenkins.tar.gz" is therefore this repo's `.github/workflows/`
directory, and the equivalent of the "Jenkins deploy guide" is this document plus
[`deployment.md`](./deployment.md).

---

## Pipeline overview

```
 push to dev  ┐
 PR → dev/main ┴─►  GitHub Actions (ci.yml)
                        │
                        ├─ backend-lint     ruff check + ruff format --check
                        ├─ frontend-lint    npm ci + npm run lint
                        └─ frontend-build   npm ci + npm run build   (needs: frontend-lint)
                        │
                        ▼
                 all checks green ──► review + merge to dev
                        │
                        ▼
        (manual, on the VM)  git pull on /opt/cs14/app
                        │
                        ▼
   docker compose -f docker-compose.prod.yml --env-file .env build && up -d
                        │
                        ▼
        Caddy  ──►  Cloudflare Tunnel  ──►  https://cs14.kazelis.top
```

CI is **fully automated** on every push/PR. Production deployment is **manual and
operator-driven** on the VM — a capstone-appropriate choice that keeps a human in front of any
change to the live demo host rather than auto-deploying on merge.

---

## Continuous integration (GitHub Actions)

Source of truth: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

### Triggers

```yaml
on:
  pull_request:
    branches: [dev, main]
  push:
    branches: [dev]
```

Checks run on every pull request targeting `dev` or `main`, and on every direct push to
`dev`. The merge gate is the PR — a branch cannot reach `dev`/`main` with red checks.

### Jobs

| Job | Runner | Working dir | Steps |
| --- | --- | --- | --- |
| `backend-lint` | `ubuntu-latest` | `backend` | `pip install ruff` → `ruff check .` → `ruff format --check .` |
| `frontend-lint` | `ubuntu-latest` | `frontend` | `npm ci` → `npm run lint` |
| `frontend-build` | `ubuntu-latest` | `frontend` | `npm ci` → `npm run build` (runs only after `frontend-lint` passes via `needs:`) |

- **`backend-lint`** enforces both correctness (`ruff check`) and a consistent format
  (`ruff format --check`) on Python 3.11, matching the backend runtime image
  (`python:3.11-slim`).
- **`frontend-lint`** runs the Next.js lint rules on Node 20.
- **`frontend-build`** proves the production build compiles; it `needs: frontend-lint` so a
  build slot is not spent on a branch that already fails lint.

### Reproducing CI locally

The same checks the runners execute can be run before pushing:

```bash
# backend lint (matches backend-lint)
cd backend && ruff check . && ruff format --check .

# frontend lint + build (matches frontend-lint and frontend-build)
cd frontend && npm ci && npm run lint && npm run build
```

Or through Docker, mirroring the validation block in the root README:

```bash
docker compose run --rm -T --no-deps frontend \
  sh -c 'npm run lint && npm run build'
docker compose exec -T backend pytest -q     # unit tests, when the stack is up
```

> Note: the backend `pytest` suite is run locally / in the running stack rather than in
> `ci.yml`. The CI workflow gates on lint + frontend build; the test suite is exercised via
> the Docker stack during development and integration testing (see
> [`CS14_ACCEPTANCE_CHECKLIST.md`](./CS14_ACCEPTANCE_CHECKLIST.md)). Wiring `pytest` into a
> CI job (with a service Postgres) is a documented next step.

---

## Branch model and review gate

From the README **Contributing** section:

- `dev` is the **integration branch**; `main` is the **release branch**.
- Feature work happens on `feature/<area>-<short-description>` branches.
- Pull requests use Conventional Commit-style titles and target `dev`.

```bash
git checkout dev && git pull
git checkout -b feature/<area>-<short-description>
# work, test, commit
git push -u origin feature/<area>-<short-description>
gh pr create --base dev
```

Code ownership is declared in [`.github/CODEOWNERS`](../.github/CODEOWNERS), which routes
review requests by area (frontend editor / participant, backend auth / posts / tracking, and
shared CI/Docker/main owned by the tech lead). The PR template
([`.github/pull_request_template.md`](../.github/pull_request_template.md)) requires a module
tag, a how-to-test section, an API-change note, and a green-lint / diff-size checklist.

---

## Build artifacts (Docker images)

CI validates source; the deployable artifacts are the two Docker images defined in the repo:

| Image | Base | Build context | Runtime |
| --- | --- | --- | --- |
| `usyd-cs14-1-backend` | `python:3.11-slim` | [`backend/Dockerfile`](../backend/Dockerfile) | `alembic upgrade head` then `uvicorn app.main:app` |
| `usyd-cs14-1-frontend` | `node:20-alpine` | [`frontend/Dockerfile`](../frontend/Dockerfile) | Next.js (`dev` locally; `build` + `start` in prod compose) |

Images are built on demand from source on the deploy host rather than pushed to a registry —
appropriate for a single-VM capstone deployment. The dev stack
([`docker-compose.yml`](../docker-compose.yml)) builds and runs all three services
(`db` + `backend` + `frontend`) for local development; the production stack
(`docker-compose.prod.yml`, on the VM) builds the same images with production env and adds the
`caddy` and `cloudflared` services.

---

## Continuous delivery (production)

Production delivery is operator-driven on the VM at `/opt/cs14` (full detail in
[`deployment.md`](./deployment.md)):

```bash
# on the VM, after a green PR is merged to dev/main
cd /opt/cs14/app && git pull

cd /opt/cs14
docker compose -f docker-compose.prod.yml --env-file .env build backend frontend
docker compose -f docker-compose.prod.yml --env-file .env up -d backend frontend
```

The backend runs `alembic upgrade head` on every container start, so schema migrations are
applied as part of each deploy. Caddy (ports 80 / 8443) reverse-proxies `/api/v1/*`, `/docs`,
`/redoc`, `/openapi.json`, and `/health` to the backend and everything else to the frontend;
Cloudflare Tunnel publishes `https://cs14.kazelis.top` without binding host port 443.

### Post-deploy smoke

After a deploy, the same checks from the deployment doc confirm the release:

```bash
curl -sf https://cs14.kazelis.top/health             # → {"status":"ok"}
DEMO_HOST='cs14.kazelis.top' ./scripts/verify_demo_public.sh
```

---

## Mapping to the delivery checklist

| Sample checklist item (CS63-1) | CS14-1 equivalent |
| --- | --- |
| #5 `Jenkins.tar.gz` | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) (GitHub Actions config, version-controlled) |
| #6 Jenkins deploy guide | This document + [`deployment.md`](./deployment.md) |

## Related docs

- [`deployment.md`](./deployment.md) — production host, Caddy, Cloudflare Tunnel, `.env`
- [`deployment-video-script.md`](./deployment-video-script.md) — clean-checkout deploy walkthrough
- [`README.md`](./README.md) — documentation index
