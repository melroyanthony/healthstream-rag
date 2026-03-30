#!/usr/bin/env bash
# HealthStream RAG - E2E Happy Path Test
# Requires the backend to be running on localhost:8000
#
# Usage:
#   cd solution/backend && uv run uvicorn app.api.main:app --port 8000 &
#   cd solution && bash scripts/test-e2e.sh

set -euo pipefail

BASE_URL="${API_URL:-http://localhost:8000}"
PASS=0
FAIL=0

check() {
    local name="$1"
    local expected_code="$2"
    local actual_code="$3"
    if [ "$actual_code" = "$expected_code" ]; then
        echo "  PASS: $name (HTTP $actual_code)"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $name (expected $expected_code, got $actual_code)"
        FAIL=$((FAIL + 1))
    fi
}

CURL_OPTS=(--connect-timeout 5 --max-time 30)

echo "=== HealthStream RAG E2E Happy Path ==="
echo "Target: $BASE_URL"
echo ""

# 1. Health check
echo "1. Health Check"
CODE=$(curl -s "${CURL_OPTS[@]}" -o /dev/null -w "%{http_code}" "$BASE_URL/health")
check "GET /health" "200" "$CODE"

# 2. Ingest documents for patient
echo "2. Ingest Documents"
CODE=$(curl -s "${CURL_OPTS[@]}" -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer patient-test-e2e" \
  -d '{
    "documents": [
      {
        "text": "Sleep session: sleep score 88, therapy hours 7.5, AHI 2.8 events/hour. Device: AutoSet CPAP.",
        "source_type": "healthkit",
        "source_id": "e2e-session-001"
      },
      {
        "text": "FHIR Condition: Obstructive Sleep Apnea G47.33. Status: active. AHI at diagnosis: 18 events/hour.",
        "source_type": "fhir",
        "source_id": "e2e-condition-001"
      }
    ],
    "collection_name": "default"
  }')
check "POST /api/v1/ingest" "200" "$CODE"

# 3. Query health data
echo "3. Query Health Data"
RESPONSE=$(curl -s "${CURL_OPTS[@]}" -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/query" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer patient-test-e2e" \
  -d '{"question": "What was my sleep score?"}')
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
RESPONSE=$(echo "$RESPONSE" | sed '$d')
CODE="$HTTP_CODE"
check "POST /api/v1/query (status)" "200" "$HTTP_CODE"
HAS_ANSWER=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if 'answer' in d else 'no')" 2>/dev/null || echo "no")
if [ "$HAS_ANSWER" = "yes" ]; then
    echo "  PASS: POST /api/v1/query returns answer"
    PASS=$((PASS + 1))
else
    echo "  FAIL: POST /api/v1/query missing answer field"
    FAIL=$((FAIL + 1))
fi

HAS_CITATIONS=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if len(d.get('citations',[])) > 0 else 'no')" 2>/dev/null || echo "no")
if [ "$HAS_CITATIONS" = "yes" ]; then
    echo "  PASS: Query response includes citations"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Query response missing citations"
    FAIL=$((FAIL + 1))
fi

HAS_DISCLAIMER=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if d.get('disclaimer','') != '' else 'no')" 2>/dev/null || echo "no")
if [ "$HAS_DISCLAIMER" = "yes" ]; then
    echo "  PASS: Query response includes disclaimer"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Query response missing disclaimer"
    FAIL=$((FAIL + 1))
fi

# 4. Create collection
echo "4. Create Collection"
CODE=$(curl -s "${CURL_OPTS[@]}" -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/collections" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-e2e" \
  -d '{"name": "e2e-test", "dimension": 384}')
check "POST /api/v1/collections" "201" "$CODE"

# 5. List collections
echo "5. List Collections"
CODE=$(curl -s "${CURL_OPTS[@]}" -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer admin-e2e" \
  "$BASE_URL/api/v1/collections")
check "GET /api/v1/collections" "200" "$CODE"

# 6. Delete collection
echo "6. Delete Collection"
CODE=$(curl -s "${CURL_OPTS[@]}" -o /dev/null -w "%{http_code}" -X DELETE \
  -H "Authorization: Bearer admin-e2e" \
  "$BASE_URL/api/v1/collections/e2e-test")
check "DELETE /api/v1/collections/e2e-test" "204" "$CODE"

# 7. Verify deletion (should 404)
echo "7. Verify Deletion"
CODE=$(curl -s "${CURL_OPTS[@]}" -o /dev/null -w "%{http_code}" -X DELETE \
  -H "Authorization: Bearer admin-e2e" \
  "$BASE_URL/api/v1/collections/e2e-test")
check "DELETE /api/v1/collections/e2e-test (deleted)" "404" "$CODE"

echo ""
echo "=== Results ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo "Total:  $((PASS + FAIL))"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
echo "All E2E tests passed!"
