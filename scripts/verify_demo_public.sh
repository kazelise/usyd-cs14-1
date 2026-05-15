#!/usr/bin/env bash
# Smoke-check public demo endpoints (no credentials).
# Usage: DEMO_HOST='cs14.kazelis.top' ./scripts/verify_demo_public.sh
# Optional: DEMO_SHARE_CODE='oYmBN-pj9IhZ3pT9' (default below matches coordination staging).

set -euo pipefail

HOST="${DEMO_HOST:-cs14.kazelis.top}"
CODE="${DEMO_SHARE_CODE:-oYmBN-pj9IhZ3pT9}"
BASE="https://${HOST}"

echo "Checking ${BASE} (share_code=${CODE})"

curl -sf "${BASE}/health" | grep -q '"ok"' || {
  echo "FAIL: /health did not return status ok"
  exit 1
}

for lang in en zh; do
  body="$(curl -sf "${BASE}/api/v1/surveys/public/${CODE}?language=${lang}")" || {
    echo "FAIL: public survey fetch failed for language=${lang}"
    exit 1
  }
  echo "${body}" | grep -q '"status":"published"' || {
    echo "FAIL: survey not published for language=${lang}"
    exit 1
  }
done

echo "OK: health + published public survey (en + zh)"
