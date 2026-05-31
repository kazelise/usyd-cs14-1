# Deployment guide — video script

Recording script for the **Deployment guide video** (final-delivery item #1). It walks a
viewer from a clean checkout to a running stack: `docker compose up` → migrations → seed →
a working URL. Read the narration lines aloud and run the commands in the shaded blocks in
order. Every command here matches the repo as committed — the local stack in the root
[`docker-compose.yml`](../docker-compose.yml), the seed in
[`backend/scripts/seed_client_demo.py`](../backend/scripts/seed_client_demo.py), and the
smoke checks in [`scripts/verify_demo_public.sh`](../scripts/verify_demo_public.sh).

For the production host layout (Caddy, Cloudflare Tunnel, `docker-compose.prod.yml`) see
[`deployment.md`](./deployment.md); for the product walkthrough see
[`DEMO_RUNBOOK.md`](./DEMO_RUNBOOK.md). This script is the **deploy-it-from-scratch** angle,
not the product demo.

---

## Before you hit record

- Quit anything already bound to ports `3000`, `8000`, `5432` so the demo ports are free
  (`docker compose down` in any old checkout, stop a local Postgres, etc.).
- Have Docker Desktop running; confirm with `docker version`.
- Start in a clean clone of the repo (or `git clean -fdx`-equivalent state) so the viewer
  sees the real first-run experience, including the image build.
- Optional: pre-pull `postgres:16-alpine` so the build step isn't waiting on a registry
  download mid-take (`docker pull postgres:16-alpine`).
- Recommended terminal width ~100 cols; clear the scrollback right before each command so
  the capture is clean.

Target length: **4–6 minutes**. The image build (Section 2) is the only slow part — either
let it play at speed or cut to a "build finished" marker.

---

## Section 0 — Framing (say to camera, ~20s)

> "This is the CS14-1 social-media survey platform. I'll deploy the whole stack from a
> clean checkout using Docker Compose — Postgres, the FastAPI backend, and the Next.js
> frontend — run the database migrations, seed the demo data, and open a working URL. No
> manual install steps; everything is in the compose file."

---

## Section 1 — Show the inputs (~30s)

Narrate while you display the two files that define the deployment:

```bash
# the stack definition: db + backend + frontend, one file
cat docker-compose.yml
```

> "Three services. Postgres 16 with a health check, the backend which runs
> `alembic upgrade head` and then `uvicorn` on start, and the frontend on Next.js. The
> backend waits for the database health check before it starts."

Call out the env defaults so the viewer understands what is dev-only:

> "For local deployment the compose file ships safe development defaults — the dev database
> password, `DEBUG=true`, and `--reload`. Production overrides every one of these from a
> server-side `.env`; that layout is in `docs/deployment.md`."

---

## Section 2 — Build and start the stack (~60–90s)

```bash
docker compose up -d --build
```

> "`up -d --build` builds the backend and frontend images and starts all three services in
> the background. First run builds from scratch, so this is the slow step."

Wait for the command to return, then show the services are up and the DB is healthy:

```bash
docker compose ps
```

> "All three are up, and Postgres reports `healthy` — that's the health check the backend
> depends on."

If you want to show the migrations applying on backend start:

```bash
docker compose logs backend | grep -i "alembic\|Running upgrade\|Application startup" | head
```

> "On start the backend already ran `alembic upgrade head`, so the schema is in place before
> it serves traffic. In production the same command runs on every container start."

---

## Section 3 — Confirm migrations explicitly (~20s)

Even though the backend auto-migrates on start, show the migration head to make it concrete:

```bash
docker compose exec backend alembic current
```

> "`alembic current` confirms the database is at the latest migration head."

---

## Section 4 — Seed the demo data (~30s)

```bash
docker compose exec backend python -m scripts.seed_client_demo
```

> "This seeds the demo surveys — the main walkthrough survey `CS14DEMO2026` plus the gallery
> codes — with bilingual content. It's idempotent: it wipes and recreates the demo data each
> run, so re-running is always safe."

---

## Section 5 — Prove it's working (~45s)

Hit the health endpoint and the OpenAPI title from the host:

```bash
curl -s http://localhost:8000/health
# → {"status":"ok"}

curl -s http://localhost:8000/openapi.json | head -c 80
# → {"openapi":"3.1.0","info":{"title":"CS14-1 Survey Platform" ...
```

> "The backend answers on `/health`, and `/openapi.json` confirms it's our app."

Optional one-liner smoke over the seeded public survey (plain HTTP, local stack):

```bash
DEMO_HOST='localhost:8000' DEMO_SCHEME='http' \
  DEMO_SHARE_CODES='CS14DEMO2026' ./scripts/verify_demo_public.sh
```

> "The repo's smoke script curls `/health` and the seeded survey in both English and Chinese
> — green means the data is live."

---

## Section 6 — Open the URL (~30s)

Switch to the browser:

> "And here's the running platform on `http://localhost:3000`. The frontend talks to the
> backend at `http://127.0.0.1:8000/api/v1`. Researcher login is here; the seeded participant
> survey is at `/survey/CS14DEMO2026`."

Open, in order:

1. `http://localhost:3000/` — frontend loads.
2. `http://localhost:3000/survey/CS14DEMO2026` — seeded participant survey renders.

> "That's a clean-checkout deployment: build, migrate, seed, and a working URL, all from the
> compose file. For the production host — Caddy, Cloudflare Tunnel, HTTPS for the webcam
> calibration — see `docs/deployment.md`."

---

## Section 7 — Tear down (off-camera or as a tail, ~10s)

```bash
docker compose down            # stop services, keep the pgdata volume
docker compose down -v         # also drop the database volume for a truly clean state
```

> "`down` stops everything; add `-v` to also drop the Postgres volume if you want the next
> run to start from an empty database."

---

## One-page command cheat sheet

Run top to bottom for a full clean-checkout deployment:

```bash
docker compose up -d --build                                  # build + start db, backend, frontend
docker compose ps                                             # confirm services up, db healthy
docker compose exec backend alembic current                  # confirm migrations at head
docker compose exec backend python -m scripts.seed_client_demo   # seed demo surveys
curl -s http://localhost:8000/health                          # → {"status":"ok"}
# browser: http://localhost:3000/  and  /survey/CS14DEMO2026
docker compose down                                           # tear down (add -v to drop the db volume)
```

## If something goes wrong on camera

| Symptom | Quick fix |
| --- | --- |
| Port already in use on `up` | Stop the other process or set `BACKEND_PORT` / `FRONTEND_PORT` / `DB_PORT` env vars before `up`. |
| Backend restarts / can't reach db | `docker compose ps` — wait for db `healthy`; check `docker compose logs db`. |
| `/health` not answering yet | Backend still building or migrating; `docker compose logs -f backend` until `Application startup complete`. |
| Seed errors about an existing account | Seed is idempotent on the demo codes; re-run it, or `docker compose down -v` then `up` for a clean DB. |
| Frontend 404 / API network error | Confirm `NEXT_PUBLIC_API_URL` resolves to `http://127.0.0.1:8000/api/v1` (compose default) and the backend is up. |

## Related docs

- [`deployment.md`](./deployment.md) — production host, Caddy, Cloudflare Tunnel, `.env`
- [`DEMO_RUNBOOK.md`](./DEMO_RUNBOOK.md) — product walkthrough script for the client meeting
- [`README.md`](./README.md) — documentation index
