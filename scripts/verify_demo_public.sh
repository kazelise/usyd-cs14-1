#!/usr/bin/env bash
# Smoke-check public demo endpoints (no credentials).
# Usage:
#   DEMO_HOST='localhost:8000' DEMO_SCHEME='http' ./scripts/verify_demo_public.sh
#   DEMO_HOST='cs14.kazelis.top' ./scripts/verify_demo_public.sh
#
# Optional: DEMO_SHARE_CODES='CS14DEMO2026 CS14X2026 ...' overrides the defaults.

set -euo pipefail

HOST="${DEMO_HOST:-cs14.kazelis.top}"
SCHEME="${DEMO_SCHEME:-https}"
DEFAULT_CODES=(
  CS14DEMO2026 CS14X2026 CS14IG2026 CS14RED2026 CS14TRUTH26 CS14BSKY2026 CS14DOUYIN26
)
read -r -a SHARE_CODES <<< "${DEMO_SHARE_CODES:-${DEFAULT_CODES[*]}}"
BASE="${SCHEME}://${HOST}"

echo "Checking ${BASE} (codes: ${SHARE_CODES[*]})"

curl -sf "${BASE}/health" | grep -q '"ok"' || {
  echo "FAIL: ${BASE}/health did not return status ok"
  exit 1
}

for CODE in "${SHARE_CODES[@]}"; do
  for lang in en zh; do
    url="${BASE}/api/v1/surveys/public/${CODE}?language=${lang}"
    body="$(curl -sf "${url}")" || {
      echo "FAIL: public survey fetch failed for share_code=${CODE} language=${lang}"
      exit 1
    }
    echo "${body}" | grep -q '"status":"published"' || {
      echo "FAIL: survey not published for share_code=${CODE} language=${lang}"
      exit 1
    }
    echo "${body}" | grep -q '"title"' || {
      echo "FAIL: unexpected payload missing title for share_code=${CODE}"
      exit 1
    }
  done
done

echo "OK: health + published public surveys (en + zh) for fixed share codes"
