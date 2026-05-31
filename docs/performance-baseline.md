# Performance baseline (runtime)

Final-delivery item #27 (Performance Testing). The query / eager-loading analysis is owned by
Backend (Zhenyu); this document and [`scripts/perf_baseline.sh`](../scripts/perf_baseline.sh)
cover the **runtime** side: end-to-end response latency for the public read endpoints, measured
from a client's point of view. It is a smoke-level baseline, not a load/stress test.

It pairs with [`scripts/verify_demo_public.sh`](../scripts/verify_demo_public.sh):
`verify_demo_public.sh` checks the endpoints answer **correctly**; `perf_baseline.sh` checks
how **fast** they answer.

## What it measures

For each endpoint, the script issues `SAMPLES` (default 30) sequential GET requests and reports
`min / p50 / p95 / max` of `curl`'s `time_total` (full request→response, including TLS where
applicable), in milliseconds. Non-200 responses are excluded and counted.

Endpoints covered:

| Label | Path | Why |
| --- | --- | --- |
| `health` | `/health` | Cheapest endpoint — server/network floor, no DB. |
| `openapi` | `/openapi.json` | Static-ish schema render; app overhead without DB reads. |
| `public-survey-en` | `/api/v1/surveys/public/CS14DEMO2026?language=en` | Real DB read with eager-loaded posts/questions — the path the schema migration touched. |
| `public-survey-zh` | `/api/v1/surveys/public/CS14DEMO2026?language=zh` | Same read in the second seeded locale. |

The public-survey endpoints are the meaningful ones for item #27: they exercise the
eager-loading on the unified schema adapter, so their latency is what to watch for regressions
after the legacy-schema deprecation.

## Running it

Against the local stack (bring it up and seed first):

```bash
docker compose up -d
docker compose exec backend python -m scripts.seed_client_demo

DEMO_HOST='localhost:8000' DEMO_SCHEME='http' ./scripts/perf_baseline.sh
```

Against the deployed host:

```bash
DEMO_HOST='cs14.kazelis.top' ./scripts/perf_baseline.sh
```

More samples for a steadier p95:

```bash
SAMPLES=100 DEMO_HOST='localhost:8000' DEMO_SCHEME='http' ./scripts/perf_baseline.sh
```

## Example output

```
Performance baseline against http://localhost:8000
Samples per endpoint: 30

endpoint                      n  min(ms)  p50(ms)  p95(ms)  max(ms)
---------------------- -------- ------- ------- ------- -------
health                       30     ...     ...     ...     ...
openapi                      30     ...     ...     ...     ...
public-survey-en             30     ...     ...     ...     ...
public-survey-zh             30     ...     ...     ...     ...
```

Record the numbers as the post-migration baseline. To check for a regression introduced by the
schema migration, compare the `public-survey-*` rows against a run on the pre-migration commit
(same host, same `SAMPLES`).

## Interpreting results

- `health` and `openapi` establish the app/network floor with little or no DB work. The gap
  between those and `public-survey-*` is roughly the DB read + serialization cost.
- Watch **p95**, not just min/median — a high p95 with a low median points at occasional slow
  queries (e.g. an eager-load fanning out) rather than a uniformly slow path.
- Local numbers are not comparable to deployed numbers: the deployed host adds TLS, Caddy, and
  Cloudflare Tunnel hops. Compare like-for-like (local vs local, deployed vs deployed).

## Scope and next steps

This is a single-client sequential baseline — enough to catch a gross regression from the
schema change for a capstone deliverable. It is **not** a concurrency/throughput test. If the
team wants load characteristics, the documented next step is a concurrency tool (e.g. `hey`,
`wrk`, or `locust`) against the same endpoints, coordinated with Backend's query-count
analysis.

## Related docs

- [`scripts/verify_demo_public.sh`](../scripts/verify_demo_public.sh) — correctness smoke
- [`architecture.md`](./architecture.md) — subsystem overview
- [`tracking-data-flow.md`](./tracking-data-flow.md) — data model behind the reads
