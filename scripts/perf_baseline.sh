#!/usr/bin/env bash
#
# perf_baseline.sh — runtime latency baseline for the CS14-1 backend.
#
# Final-delivery item #27 (Performance Testing), runtime side. Supports the
# query/eager-loading baseline owned by Backend (Zhenyu) by measuring end-to-end
# response latency for the public read endpoints from a client's point of view.
# It is a smoke-level baseline, not a load test: it issues a fixed number of
# sequential requests per endpoint and reports min / median / p95 / max latency.
#
# Pairs with scripts/verify_demo_public.sh (which checks correctness); this
# script checks how fast those same endpoints answer.
#
# Usage:
#   # against the local stack (docker compose up)
#   DEMO_HOST='localhost:8000' DEMO_SCHEME='http' ./scripts/perf_baseline.sh
#
#   # against the deployed host
#   DEMO_HOST='cs14.kazelis.top' ./scripts/perf_baseline.sh
#
#   # more samples per endpoint (default 30)
#   SAMPLES=100 DEMO_HOST='localhost:8000' DEMO_SCHEME='http' ./scripts/perf_baseline.sh
#
# Env:
#   DEMO_HOST     host[:port]           (default: localhost:8000)
#   DEMO_SCHEME   http | https          (default: https)
#   SAMPLES       requests per endpoint (default: 30)
#   SHARE_CODE    seeded survey code    (default: CS14DEMO2026)
#
# Requires: bash, curl, sort, awk. No extra dependencies.

set -u

DEMO_HOST="${DEMO_HOST:-localhost:8000}"
DEMO_SCHEME="${DEMO_SCHEME:-https}"
SAMPLES="${SAMPLES:-30}"
SHARE_CODE="${SHARE_CODE:-CS14DEMO2026}"

BASE="${DEMO_SCHEME}://${DEMO_HOST}"

# endpoint label | path
ENDPOINTS=(
  "health|/health"
  "openapi|/openapi.json"
  "public-survey-en|/api/v1/surveys/public/${SHARE_CODE}?language=en"
  "public-survey-zh|/api/v1/surveys/public/${SHARE_CODE}?language=zh"
)

echo "Performance baseline against ${BASE}"
echo "Samples per endpoint: ${SAMPLES}"
echo ""
printf "%-22s %8s %8s %8s %8s %8s\n" "endpoint" "n" "min(ms)" "p50(ms)" "p95(ms)" "max(ms)"
printf "%-22s %8s %8s %8s %8s %8s\n" "----------------------" "----" "-------" "-------" "-------" "-------"

overall_fail=0

for entry in "${ENDPOINTS[@]}"; do
  label="${entry%%|*}"
  path="${entry#*|}"
  url="${BASE}${path}"

  samples=()
  failures=0
  for _ in $(seq 1 "${SAMPLES}"); do
    # %{time_total} is seconds with fractional part; convert to ms.
    out=$(curl -s -o /dev/null -w "%{http_code} %{time_total}" "${url}" 2>/dev/null)
    code="${out%% *}"
    t="${out##* }"
    if [ "${code}" != "200" ]; then
      failures=$((failures + 1))
      continue
    fi
    ms=$(awk -v s="${t}" 'BEGIN { printf "%.1f", s * 1000 }')
    samples+=("${ms}")
  done

  n="${#samples[@]}"
  if [ "${n}" -eq 0 ]; then
    printf "%-22s %8s %8s %8s %8s %8s\n" "${label}" "0" "-" "-" "-" "-"
    echo "    !! all ${SAMPLES} requests failed (non-200 or unreachable)"
    overall_fail=1
    continue
  fi

  sorted=$(printf "%s\n" "${samples[@]}" | sort -n)
  stats=$(printf "%s\n" "${sorted}" | awk '
    { a[NR] = $1 }
    END {
      n = NR
      p50i = int((n - 1) * 0.50) + 1
      p95i = int((n - 1) * 0.95) + 1
      printf "%s %s %s %s", a[1], a[p50i], a[p95i], a[n]
    }')
  read -r vmin vp50 vp95 vmax <<< "${stats}"
  printf "%-22s %8s %8s %8s %8s %8s\n" "${label}" "${n}" "${vmin}" "${vp50}" "${vp95}" "${vmax}"
  if [ "${failures}" -gt 0 ]; then
    echo "    note: ${failures}/${SAMPLES} non-200 responses excluded"
  fi
done

echo ""
if [ "${overall_fail}" -eq 0 ]; then
  echo "Baseline complete. Record these numbers alongside the schema-migration"
  echo "before/after comparison for item #27."
else
  echo "Baseline finished with endpoint failures — check the stack is up and seeded:"
  echo "  docker compose up -d && docker compose exec backend python -m scripts.seed_client_demo"
  exit 1
fi
