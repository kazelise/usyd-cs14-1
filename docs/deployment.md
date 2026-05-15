# Deployment and production operations

This document closes the operational gap called out in [`CS14_ACCEPTANCE_CHECKLIST.md`](./CS14_ACCEPTANCE_CHECKLIST.md): environment variables, migrations, HTTPS/camera constraints, CORS, the production compose/Caddy layout, and a repeatable smoke checklist. For a longer narrative, see also the VitePress page [`docs-site/docs/project/setup-deployment.md`](../docs-site/docs/project/setup-deployment.md).

### Source-of-truth note (git vs demo host)

`docker-compose.prod.yml` and the production `Caddyfile` referenced below are deployed under `/opt/cs14` on the demo VM. They are **not** currently checked into this repository (only the dev [`docker-compose.yml`](../docker-compose.yml) lives in git). Treat the files on the server as canonical until the team vendors them into the repo; after `rsync` or manual edits on the host, consider copying them back for version control.

## Current deployed environment

| Item | Value |
| --- | --- |
| Public URL | `https://cs14.kazelis.top/` |
| Public docs URL | `https://cs14-docs.kazelis.top/` |
| Host | Debian 12 (Bookworm), single VM (`windeza-jp`) |
| Deploy root | `/opt/cs14` |
| App source mount | `/opt/cs14/app` (this repo checked out on the server) |
| Compose file | `/opt/cs14/docker-compose.prod.yml` |
| Reverse proxy | Caddy 2, config at `/opt/cs14/Caddyfile`, reached publicly through Cloudflare Tunnel |
| TLS | Cloudflare edge TLS for `cs14.kazelis.top` / `cs14-docs.kazelis.top`; legacy `sslip.io:8443` TLS remains available through Caddy |
| Active ports | `80` and `8443` for legacy direct access; public custom domains use Cloudflare Tunnel because port `443` is occupied by an unrelated `sing-box` process on this VM |
| Containers | `cs14_db_1` (postgres:16-alpine), `cs14_backend_1`, `cs14_frontend_1`, `cs14_caddy_1`, `cs14_cloudflared_1` |

The host port `443` is unavailable on this server. The public custom domains therefore use Cloudflare Tunnel to reach Caddy over the Docker network without exposing another host port. The legacy `sslip.io:8443` URL still works as a fallback.

`docker-compose.prod.yml` differs from the root-level `docker-compose.yml` used for local development in four important ways:

1. It reads all secrets from `/opt/cs14/.env` instead of hard-coded dev values.
2. The backend runs `uvicorn` **without** `--reload`, and the frontend runs `npm run build && npm run start` (production build), not `next dev`.
3. It adds a `caddy` service that owns ports 80 and 8443 and reverse-proxies to the internal services.
4. It adds a `cloudflared` service that exposes `cs14.kazelis.top` and `cs14-docs.kazelis.top` through Cloudflare Tunnel without binding host port 443.

## Environment variables

### Production `.env` (server: `/opt/cs14/.env`, mode 0600)

| Variable | Purpose |
| --- | --- |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Postgres credentials and DB name used by both `db` and `backend` services. |
| `SECRET_KEY` | JWT signing secret — strong random value, never commit. |
| `CORS_ORIGINS` | Comma-separated allow list of browser origins (e.g. `https://cs14.kazelis.top`). Must include every exact origin (scheme + host + port) used by participants or researchers. |
| `NEXT_PUBLIC_API_URL` | Public base URL for the REST API **including** `/api/v1` (e.g. `https://cs14.kazelis.top/api/v1`). Baked into the Next.js build at image build time — changing it requires a rebuild of the `frontend` service. |
| `APP_DOMAIN` | Legacy direct-access hostname used by Caddy for the `http://` -> `https://:8443` redirect and direct Caddy TLS issuance (e.g. `151.244.134.156.sslip.io`). |
| `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare Tunnel token for the public custom domains. Keep it only on the server; never paste it into tickets, docs, or commits. |

The `.env` file is kept out of version control. To rotate any secret, edit `/opt/cs14/.env` on the host then rebuild and restart the affected service.

### Local development defaults

For local Compose runs, the root [`docker-compose.yml`](../docker-compose.yml) hard-codes development values (`cs14:cs14_dev_password`, `dev-secret-change-in-production`, `DEBUG=true`, `--reload`). Those defaults are not used in production.

### Optional backend variables

| Variable | Purpose |
| --- | --- |
| `DEBUG` | Set `false` in production (default in `docker-compose.prod.yml`). Verbose errors and Swagger expose more in `true`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Override JWT lifetime; default is long-lived for lab use — tighten if required by policy. |

## Caddy reverse proxy

`/opt/cs14/Caddyfile` (excerpt):

```caddy
{
    http_port 80
    https_port 8443
}

http://{$APP_DOMAIN} {
    redir https://{$APP_DOMAIN}:8443{uri} permanent
}

(app_routes) {
    encode gzip
    handle /api/v1/*     { reverse_proxy backend:8000 }
    handle /docs*        { reverse_proxy backend:8000 }
    handle /redoc*       { reverse_proxy backend:8000 }
    handle /openapi.json { reverse_proxy backend:8000 }
    handle /health       { reverse_proxy backend:8000 }
    handle               { reverse_proxy frontend:3000 }
}

http://cs14.kazelis.top {
    import app_routes
}

http://cs14-docs.kazelis.top {
    encode gzip
    root * /srv/docs
    try_files {path} {path}/ /index.html
    file_server
}

https://{$APP_DOMAIN}:8443 {
    import app_routes
}
```

Anything under `/api/v1/`, plus `/docs`, `/redoc`, `/openapi.json` and `/health`, is proxied to the FastAPI backend. Everything else on `cs14.kazelis.top` falls through to the Next.js frontend. `cs14-docs.kazelis.top` serves the VitePress static build from `/opt/cs14/docs-site-dist`. Public certificate management is handled by Cloudflare edge TLS for the custom domains; Caddy still manages the legacy direct `sslip.io:8443` certificate.

## Operate the production stack

All commands run on the VM in `/opt/cs14`.

```bash
# bring everything up
docker compose -f docker-compose.prod.yml --env-file .env up -d

# rebuild after pulling code
docker compose -f docker-compose.prod.yml --env-file .env build backend frontend
docker compose -f docker-compose.prod.yml --env-file .env up -d backend frontend

# tail logs
docker compose -f docker-compose.prod.yml logs -f --tail=100 backend
docker compose -f docker-compose.prod.yml logs -f --tail=100 caddy

# inspect / one-shot psql
docker exec -it cs14_db_1 psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

Container names use the legacy `cs14_<service>_1` form (this VM still runs the v1 compose CLI binding); newer Docker Compose installs use `cs14-<service>-1` — adjust accordingly if the host gets upgraded.

## Database migrations

Before serving traffic against a fresh database (or after pulling new migrations):

```bash
cd backend
alembic upgrade head
```

In production, the backend service runs `alembic upgrade head` on every container start (see `docker-compose.prod.yml`'s `backend.command`). For destructive or long-running migrations, test on a copy first.

## HTTPS and webcam calibration

Browsers only expose camera APIs in a **secure context**: `https:` (or `http://localhost` for development). Production participant links **must** use HTTPS on a hostname or IP with a valid/trusted certificate; otherwise calibration and gaze capture will fail or prompt inconsistently. The canonical participant host is `https://cs14.kazelis.top/`. The legacy `sslip.io:8443` route is also a secure context as long as the TLS cert validates, but it is no longer the preferred demo URL.

## CORS

The FastAPI app uses `CORS_ORIGINS` as an explicit allow list. After deployment, if the browser shows CORS errors, verify:

1. The participant or admin URL you open matches one of the listed origins (scheme + host + optional port). The canonical custom domain origin is `https://cs14.kazelis.top`; the legacy fallback origin includes `:8443`.
2. The frontend was built with `NEXT_PUBLIC_API_URL` pointing at the **public** API URL clients can reach.

## Smoke checklist (deployed or staging)

Run through this after DNS, TLS, and env are in place. Replace `<host>` with your deployed host (currently `cs14.kazelis.top`).

```bash
curl -sf https://<host>/health
# → {"status":"ok"}

curl -sf https://<host>/openapi.json | head -c 80
# → {"openapi":"3.1.0","info":{"title":"CS14-1 Survey Platform" ...
```

Optional hardening spot-check (participant routes require `participant_token` in JSON or query; omission → **422**, wrong token → **404**). The example below omits the token on purpose; you should see HTTP **422**:

```bash
curl -s -o /dev/null -w "%{http_code}\\n" -X POST \
  "https://<host>/api/v1/surveys/responses/1/interact" \
  -H "Content-Type: application/json" \
  -d '{"post_id":1,"action_type":"like","comment_text":null}'
```

Then in a browser:

1. Open the public frontend; researcher register or login works.
2. Create a survey with at least one post and one question block; publish; open the share link in a fresh profile or incognito.
3. Participant: consent, pick a language, complete calibration (if enabled), interact, finish.
4. Repeat step 3 in a **second** locale (e.g. English then Chinese) to confirm the two-language path. The seed demo survey already has English + Chinese content — see [`DEMO_RUNBOOK.md`](./DEMO_RUNBOOK.md).
5. Admin: analytics reflect the session; export CSV and JSON and confirm columns include response metadata, calibration-related fields, and tracking fields as expected.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Camera never prompts | Insecure context (page on `http://` or self-signed cert), permission blocked at OS/browser level, or HTTPS port unreachable. |
| API 401 / Network error from browser | Wrong `NEXT_PUBLIC_API_URL` (must be `https://cs14.kazelis.top/api/v1` for the public demo), mixed content (HTTPS page calling HTTP API), or CORS not listing the frontend origin. |
| `422` / `404` from participant PATCH/POST | Body or query is missing `participant_token`, or the token does not match the `response_id`. The participant UI fills this automatically — hitting APIs with raw `curl` requires copying the token from a browser session. |
| `[object Object]` rendered as an error | Backend returned a structured 4xx/5xx body; check the browser network tab for the `detail` field and the backend logs for the upstream error. |
| Empty CSV/JSON export | Filters too narrow, or no completed responses yet — finish at least one participant session first. |
| Migrations fail on startup | Database user lacks DDL rights, or the `pgdata` volume points at an older major version. |
| HTTPS reachable but `/api/v1/...` returns frontend HTML | Caddyfile path matchers were edited and `/api/v1/*` is no longer routed to `backend:8000`. Restart Caddy after fixing: `docker compose -f docker-compose.prod.yml restart caddy`. |

## Coordination demo URL

The parent coordination issue references this shared HTTPS demo host for client review:

- Frontend / participant entry: `https://cs14.kazelis.top/`
- API base: `https://cs14.kazelis.top/api/v1`
- Swagger / OpenAPI: `https://cs14.kazelis.top/docs`
- Public docs site: `https://cs14-docs.kazelis.top/`

Use this URL only with credentials and data approved for demo. Do not paste passwords, JWTs, or `.env` values into tickets or committed docs — the live researcher demo account is communicated out-of-band; see [`DEMO_RUNBOOK.md`](./DEMO_RUNBOOK.md) for the pointer.
