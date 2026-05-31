# Server detail & credentials — TEMPLATE

> ⚠️ **This is a template. Do not commit real secrets to git.**
>
> Final-delivery item #4 (server detail & credentials) must be handed in as a **separate,
> access-controlled file** — not in the repository. This template lists *what* to record and
> *where it lives*, using placeholders only. Fill a private copy (Google Drive restricted
> doc, password manager, or the course submission channel) with the real values and submit
> that copy. Never paste real passwords, tokens, or private keys into tickets, commits, docs,
> or chat.
>
> The single source of truth for live secrets is `/opt/cs14/.env` on the VM (mode `0600`),
> which is already kept out of version control. This document is the *index* of credentials,
> not their store.

---

## 1. Host / server

| Field | Value (fill privately) |
| --- | --- |
| Provider | `<cloud provider / VPS host>` |
| Region | `<region>` |
| Hostname | `windeza-jp` |
| OS | Debian 12 (Bookworm) |
| Public IP | `<x.x.x.x>` |
| SSH user | `<ssh-user>` |
| SSH access method | `<ssh key — private key held by: ____ ; never in git>` |
| SSH port | `<22 or custom>` |
| Sudo / root access | `<who has it>` |
| Deploy root | `/opt/cs14` |
| App checkout | `/opt/cs14/app` |

## 2. Domains / DNS

| Field | Value |
| --- | --- |
| App domain | `cs14.kazelis.top` |
| Docs domain | `cs14-docs.kazelis.top` |
| Legacy direct host | `<ip>.sslip.io` (port 8443) |
| DNS / registrar | `<where the domain is managed>` |
| DNS account owner | `<who controls the registrar / Cloudflare DNS>` |

## 3. TLS / edge

| Field | Value |
| --- | --- |
| Public TLS | Cloudflare edge TLS for the custom domains |
| Tunnel | Cloudflare Tunnel (`cloudflared` container) |
| Cloudflare account | `<account email / owner — not the password>` |
| Cloudflare Tunnel token | **secret** — lives only in `/opt/cs14/.env` as `CLOUDFLARE_TUNNEL_TOKEN` |
| Legacy direct TLS | Caddy-managed cert for `sslip.io:8443` |

## 4. Application secrets (location, not values)

All real values live in `/opt/cs14/.env` (mode `0600`) on the VM. Record **where each one is
held**, not the value:

| Variable | Purpose | Held in |
| --- | --- | --- |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Postgres credentials | `/opt/cs14/.env` |
| `SECRET_KEY` | JWT signing secret (strong random) | `/opt/cs14/.env` |
| `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare Tunnel auth | `/opt/cs14/.env` |
| `CORS_ORIGINS` | Browser allow-list | `/opt/cs14/.env` |
| `NEXT_PUBLIC_API_URL` | Public API base (baked into frontend build) | `/opt/cs14/.env` |
| `APP_DOMAIN` | Legacy direct-access hostname for Caddy | `/opt/cs14/.env` |

See [`deployment.md`](./deployment.md) for the full meaning of each variable.

## 5. Demo / examiner accounts

The disposable **researcher** demo account is communicated out-of-band (see
[`DEMO_RUNBOOK.md`](./DEMO_RUNBOOK.md)) and may be reset between rehearsals. **Do not record
its password here.** Record only:

| Field | Value |
| --- | --- |
| Sign-in URL | `https://cs14.kazelis.top/auth` |
| Demo researcher email | `<recorded in the private credentials doc>` |
| Demo researcher password | `<recorded in the private credentials doc — never in git>` |
| Who can reset it | `<name>` |

## 6. Access / ownership summary

| Asset | Primary owner | Backup owner |
| --- | --- | --- |
| VM SSH | `<name>` | `<name>` |
| Cloudflare / DNS | `<name>` | `<name>` |
| `/opt/cs14/.env` on host | `<name>` | `<name>` |
| Demo account reset | `<name>` | `<name>` |

---

## Handover checklist

- [ ] Private copy of this template filled with real values and stored in the restricted
      submission channel (not git).
- [ ] `/opt/cs14/.env` is mode `0600` and owned by the deploy user only.
- [ ] At least two team members can SSH to the VM and read `/opt/cs14/.env`.
- [ ] Cloudflare / DNS account has a named owner and a backup.
- [ ] Demo researcher account reset procedure is written down and assigned.
- [ ] No real secret appears anywhere in the git history (`git log -p` spot-check on `.env`,
      tokens, passwords).
