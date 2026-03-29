#!/usr/bin/env bash
# HealthStream RAG — Interactive Demo Script
#
# Starts the local server, ingests sample data, and runs demo queries.
# Requires: uv, .env with ANTHROPIC_API_KEY set
#
# Usage:
#   cd solution/backend
#   bash scripts/demo.sh

set -euo pipefail

BASE_URL="http://localhost:8000"
AUTH_A="Authorization: Bearer synthetic-patient-001"
AUTH_B="Authorization: Bearer synthetic-patient-002"

echo "============================================"
echo "  HealthStream RAG — Interactive Demo"
echo "============================================"
echo ""

# Check if server is running
if ! curl -s "$BASE_URL/health" > /dev/null 2>&1; then
    echo "[!] Server not running. Starting in background..."
    uv run uvicorn app.api.main:app --port 8000 &
    SERVER_PID=$!
    sleep 3
    echo "    Server started (PID: $SERVER_PID)"
else
    echo "[+] Server already running at $BASE_URL"
    SERVER_PID=""
fi

echo ""
echo "--- Step 1: Health Check ---"
curl -s "$BASE_URL/health" | python3 -m json.tool
echo ""

echo "--- Step 2: Ingest Patient A (Sleep Apnea patient) ---"
curl -s -X POST "$BASE_URL/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -H "$AUTH_A" \
  -d '{
    "documents": [
      {"text": "Sleep session 2026-03-22: myAir score 88 out of 100. Therapy hours 7.5. AHI 2.8 events per hour. Mask seal: Good. Device: AirSense 11 AutoSet.", "source_type": "healthkit", "source_id": "myair-2026-03-22"},
      {"text": "Sleep session 2026-03-23: myAir score 92 out of 100. Therapy hours 8.1. AHI 1.9 events per hour. Mask seal: Excellent. Leak rate: 2.1 L/min.", "source_type": "healthkit", "source_id": "myair-2026-03-23"},
      {"text": "Weekly summary 2026-03-17 to 2026-03-23: Average myAir score 85. Average therapy hours 6.9. Average AHI 3.2. Compliance rate 86% (6 of 7 nights over 4 hours).", "source_type": "healthkit", "source_id": "weekly-summary-2026-03-23"},
      {"text": "FHIR Condition: Obstructive Sleep Apnea, ICD-10 G47.33. Status: active. Onset date: 2024-06-15. Severity: moderate. AHI at diagnosis: 18 events per hour via polysomnography.", "source_type": "fhir", "source_id": "Condition/cond-001"},
      {"text": "FHIR MedicationRequest: CPAP therapy equipment. Device: ResMed AirSense 11 AutoSet. Pressure range: 6-14 cmH2O. Prescribed by Dr. Smith. Start date: 2024-07-01.", "source_type": "fhir", "source_id": "MedicationRequest/med-001"},
      {"text": "FHIR CarePlan: Sleep apnea management. Goals: AHI below 5, therapy hours above 6 per night, myAir score above 70. Review date: 2026-04-15.", "source_type": "fhir", "source_id": "CarePlan/plan-001"}
    ]
  }' | python3 -m json.tool
echo ""

echo "--- Step 3: Ingest Patient B (Different patient) ---"
curl -s -X POST "$BASE_URL/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -H "$AUTH_B" \
  -d '{
    "documents": [
      {"text": "Sleep session 2026-03-22: myAir score 65. Therapy hours 4.2. AHI 8.5 events per hour. Mask seal: Poor. Device: AirSense 10.", "source_type": "healthkit", "source_id": "myair-b-2026-03-22"}
    ]
  }' | python3 -m json.tool
echo ""

echo "============================================"
echo "  Data ingested. Try these queries:"
echo "============================================"
echo ""
echo "--- Query 1: Sleep Score (Patient A) ---"
curl -s -X POST "$BASE_URL/api/v1/query" \
  -H "Content-Type: application/json" \
  -H "$AUTH_A" \
  -d '{"question": "What was my sleep score this week?"}' | python3 -m json.tool
echo ""

echo "--- Query 2: Device Info (Patient A) ---"
curl -s -X POST "$BASE_URL/api/v1/query" \
  -H "Content-Type: application/json" \
  -H "$AUTH_A" \
  -d '{"question": "What CPAP device am I using and what are my pressure settings?"}' | python3 -m json.tool
echo ""

echo "--- Query 3: Therapy Goals (Patient A) ---"
curl -s -X POST "$BASE_URL/api/v1/query" \
  -H "Content-Type: application/json" \
  -H "$AUTH_A" \
  -d '{"question": "What are my therapy goals?"}' | python3 -m json.tool
echo ""

echo "--- Query 4: PATIENT ISOLATION TEST (Patient B queries Patient A data) ---"
echo "    Patient B should NOT see Patient A's data:"
curl -s -X POST "$BASE_URL/api/v1/query" \
  -H "Content-Type: application/json" \
  -H "$AUTH_B" \
  -d '{"question": "What was my sleep score this week?"}' | python3 -m json.tool
echo ""

echo "============================================"
echo "  Demo complete! Server running at $BASE_URL"
echo "============================================"
echo ""
echo "Try your own queries:"
echo ""
echo '  curl -s -X POST http://localhost:8000/api/v1/query \'
echo '    -H "Content-Type: application/json" \'
echo '    -H "Authorization: Bearer synthetic-patient-001" \'
echo '    -d '"'"'{"question": "YOUR QUESTION HERE"}'"'"' | python3 -m json.tool'
echo ""
echo "More query ideas:"
echo "  - What is my AHI on therapy?"
echo "  - Has my mask seal improved?"
echo "  - What was my leak rate on March 22?"
echo "  - Am I meeting my compliance goals?"
echo "  - What conditions are in my health records?"
echo "  - When is my next review appointment?"
echo ""

if [ -n "$SERVER_PID" ]; then
    echo "To stop the server: kill $SERVER_PID"
fi
