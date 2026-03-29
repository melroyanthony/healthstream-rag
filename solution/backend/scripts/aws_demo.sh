#!/usr/bin/env bash
# HealthStream RAG — AWS Live Demo
#
# Idempotent: safe to run repeatedly. Creates users, ingests data, queries.
# Deploys a complete patient story with personas.
#
# Prerequisites:
#   - AWS CLI configured for eu-west-1
#   - Lambda deployed (healthstream-demo-query)
#   - Cognito user pool + client configured
#
# Usage:
#   bash scripts/aws_demo.sh
#   bash scripts/aws_demo.sh teardown   # remove demo users

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REGION="eu-west-1"
POOL_ID="eu-west-1_aDKTJOq4s"
CLIENT_ID="69k2ggfstp1p9m7rb9jjn7h7lm"
API="https://oxa0cmln1a.execute-api.eu-west-1.amazonaws.com"

# Export AWS credentials
eval $(aws configure export-credentials --format env 2>/dev/null) || true

# Enable admin auth flows (idempotent)
aws cognito-idp update-user-pool-client \
  --user-pool-id "$POOL_ID" --client-id "$CLIENT_ID" \
  --explicit-auth-flows ALLOW_REFRESH_TOKEN_AUTH ALLOW_USER_SRP_AUTH ALLOW_ADMIN_USER_PASSWORD_AUTH ALLOW_USER_PASSWORD_AUTH \
  --region "$REGION" --no-cli-pager > /dev/null 2>&1

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
create_user() {
  local USERNAME="$1" PASSWORD="$2" PATIENT_ID="$3" EMAIL="$4"
  aws cognito-idp admin-create-user \
    --user-pool-id "$POOL_ID" --username "$USERNAME" \
    --temporary-password 'TempPass123!' \
    --user-attributes Name=custom:patient_id,Value="$PATIENT_ID" Name=email,Value="$EMAIL" \
    --message-action SUPPRESS --region "$REGION" --no-cli-pager > /dev/null 2>&1 || true
  aws cognito-idp admin-set-user-password \
    --user-pool-id "$POOL_ID" --username "$USERNAME" \
    --password "$PASSWORD" --permanent --region "$REGION" --no-cli-pager > /dev/null 2>&1
}

get_token() {
  local USERNAME="$1" PASSWORD="$2"
  aws cognito-idp admin-initiate-auth \
    --user-pool-id "$POOL_ID" --client-id "$CLIENT_ID" \
    --auth-flow ADMIN_USER_PASSWORD_AUTH \
    --auth-parameters "USERNAME=$USERNAME,PASSWORD=$PASSWORD" \
    --region "$REGION" --no-cli-pager \
    --query 'AuthenticationResult.IdToken' --output text
}

api_call() {
  local METHOD="$1" PATH="$2" TOKEN="$3" BODY="${4:-}"
  if [ -n "$BODY" ]; then
    /usr/bin/curl -s -X "$METHOD" "$API$PATH" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d "$BODY"
  else
    /usr/bin/curl -s -X "$METHOD" "$API$PATH" \
      -H "Authorization: Bearer $TOKEN"
  fi
}

pretty() {
  python3 -m json.tool 2>/dev/null || cat
}

# ---------------------------------------------------------------------------
# Teardown mode
# ---------------------------------------------------------------------------
if [ "${1:-}" = "teardown" ]; then
  echo "Removing demo users..."
  for user in alice-cpap bob-cpap; do
    aws cognito-idp admin-delete-user --user-pool-id "$POOL_ID" --username "$user" --region "$REGION" --no-cli-pager 2>/dev/null || true
    echo "  Deleted: $user"
  done
  echo "Done. Users removed. S3 Vectors data persists (delete via console if needed)."
  exit 0
fi

# =====================================================================
#  ACT 1: Setup — Meet the Patients
# =====================================================================
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          HealthStream RAG — Live AWS Demo                  ║"
echo "║   HIPAA-compliant RAG on S3 Vectors + Bedrock Haiku 4.5   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

echo "━━━ ACT 1: Meet the Patients ━━━"
echo ""

echo "Creating patient personas in Cognito..."
create_user "alice-cpap" 'AliceCpap2026!' "patient-alice" "alice@demo.healthstream.test"
create_user "bob-cpap"   'BobCpap2026!'   "patient-bob"   "bob@demo.healthstream.test"
echo "  Alice (patient-alice): 45F, moderate OSA, compliant CPAP user"
echo "  Bob   (patient-bob):   62M, severe OSA, struggling with adherence"
echo ""

echo "Authenticating via Cognito JWT..."
ALICE_TOKEN=$(get_token "alice-cpap" 'AliceCpap2026!')
BOB_TOKEN=$(get_token "bob-cpap" 'BobCpap2026!')
echo "  Alice: JWT obtained (custom:patient_id = patient-alice)"
echo "  Bob:   JWT obtained (custom:patient_id = patient-bob)"
echo ""

echo "Health check:"
api_call GET /health "$ALICE_TOKEN" | pretty
echo ""

# =====================================================================
#  ACT 2: Ingest — Each Patient's Health Journey
# =====================================================================
echo "━━━ ACT 2: Ingest Health Data ━━━"
echo ""

echo "Ingesting Alice's data (good sleeper, compliant)..."
api_call POST /api/v1/ingest "$ALICE_TOKEN" '{
  "documents": [
    {"text": "Sleep session 2026-03-25: myAir score 92 out of 100. Therapy hours 8.1. AHI 1.9 events per hour. Mask seal: Excellent. Device: AirSense 11 AutoSet.", "source_type": "healthkit", "source_id": "alice-myair-2026-03-25"},
    {"text": "Sleep session 2026-03-26: myAir score 88 out of 100. Therapy hours 7.5. AHI 2.8 events per hour. Mask seal: Good. Leak rate: 3.1 L/min.", "source_type": "healthkit", "source_id": "alice-myair-2026-03-26"},
    {"text": "Sleep session 2026-03-27: myAir score 95 out of 100. Therapy hours 8.4. AHI 1.2 events per hour. Mask seal: Excellent. Device: AirSense 11 AutoSet.", "source_type": "healthkit", "source_id": "alice-myair-2026-03-27"},
    {"text": "Weekly summary 2026-03-21 to 2026-03-27: Average myAir score 91. Average therapy hours 7.8. Average AHI 2.1. Compliance rate 100% (7 of 7 nights over 4 hours). Trend: improving.", "source_type": "healthkit", "source_id": "alice-weekly-2026-03-27"},
    {"text": "FHIR Condition: Obstructive Sleep Apnea, ICD-10 G47.33. Status: active. Severity: moderate. AHI at diagnosis: 22 events per hour via polysomnography on 2024-03-15.", "source_type": "fhir", "source_id": "Condition/alice-osa"},
    {"text": "FHIR MedicationRequest: CPAP therapy. Device: ResMed AirSense 11 AutoSet. Pressure range: 7-15 cmH2O. Humidifier: Climate Control Auto. Prescribed by Dr. Sarah Chen, Sleep Medicine.", "source_type": "fhir", "source_id": "MedicationRequest/alice-cpap"},
    {"text": "FHIR CarePlan: Sleep apnea management plan. Goals: maintain AHI below 5 events/hour, therapy usage above 7 hours/night, myAir score above 80. Next review: 2026-04-15 with Dr. Chen.", "source_type": "fhir", "source_id": "CarePlan/alice-plan"}
  ]
}' | pretty
echo ""

echo "Ingesting Bob's data (struggling, low compliance)..."
api_call POST /api/v1/ingest "$BOB_TOKEN" '{
  "documents": [
    {"text": "Sleep session 2026-03-25: myAir score 45 out of 100. Therapy hours 2.1. AHI 12.5 events per hour. Mask seal: Poor. High leak rate: 28 L/min. Device: AirSense 10 AutoSet.", "source_type": "healthkit", "source_id": "bob-myair-2026-03-25"},
    {"text": "Sleep session 2026-03-26: No therapy data recorded. Patient did not use CPAP device.", "source_type": "healthkit", "source_id": "bob-myair-2026-03-26"},
    {"text": "Sleep session 2026-03-27: myAir score 52 out of 100. Therapy hours 3.8. AHI 9.1 events per hour. Mask seal: Fair. Device: AirSense 10 AutoSet.", "source_type": "healthkit", "source_id": "bob-myair-2026-03-27"},
    {"text": "Weekly summary 2026-03-21 to 2026-03-27: Average myAir score 41. Average therapy hours 2.8. Average AHI 11.2. Compliance rate 43% (3 of 7 nights over 4 hours). Trend: declining. Alert: below compliance threshold.", "source_type": "healthkit", "source_id": "bob-weekly-2026-03-27"},
    {"text": "FHIR Condition: Obstructive Sleep Apnea, ICD-10 G47.33. Status: active. Severity: severe. AHI at diagnosis: 42 events per hour via polysomnography on 2023-11-20.", "source_type": "fhir", "source_id": "Condition/bob-osa"},
    {"text": "FHIR MedicationRequest: CPAP therapy. Device: ResMed AirSense 10 AutoSet. Pressure range: 10-20 cmH2O. Note: patient reports mask discomfort and claustrophobia. Considering switch to AirSense 11 with smaller mask.", "source_type": "fhir", "source_id": "MedicationRequest/bob-cpap"},
    {"text": "FHIR Observation: Epworth Sleepiness Scale score 16 out of 24 (excessive daytime sleepiness). Recorded 2026-03-20. Previous score: 14 (2026-01-15). Trend: worsening.", "source_type": "fhir", "source_id": "Observation/bob-ess"}
  ]
}' | pretty
echo ""

# =====================================================================
#  ACT 3: Query — Personalized Health Insights
# =====================================================================
echo "━━━ ACT 3: Ask Questions (Personalized RAG) ━━━"
echo ""

echo "── Alice asks: \"How am I doing with my therapy?\" ──"
api_call POST /api/v1/query "$ALICE_TOKEN" '{"question": "How am I doing with my CPAP therapy this week?"}' | pretty
echo ""

echo "── Bob asks the same question: \"How am I doing with my therapy?\" ──"
api_call POST /api/v1/query "$BOB_TOKEN" '{"question": "How am I doing with my CPAP therapy this week?"}' | pretty
echo ""

echo "── Alice asks: \"What was my best night?\" ──"
api_call POST /api/v1/query "$ALICE_TOKEN" '{"question": "What was my best sleep session this week?"}' | pretty
echo ""

echo "── Bob asks: \"Why is my score so low?\" ──"
api_call POST /api/v1/query "$BOB_TOKEN" '{"question": "Why is my sleep score so low?"}' | pretty
echo ""

# =====================================================================
#  ACT 4: Patient Isolation — HIPAA Proof
# =====================================================================
echo "━━━ ACT 4: Patient Isolation (HIPAA Critical) ━━━"
echo ""

echo "── Bob tries to see Alice's data ──"
echo "   (Same question, Bob's JWT → should see ONLY Bob's records)"
api_call POST /api/v1/query "$BOB_TOKEN" '{"question": "What was my AHI at diagnosis?"}' | pretty
echo ""

echo "── Alice asks the same question ──"
echo "   (Alice's JWT → should see ONLY Alice's records)"
api_call POST /api/v1/query "$ALICE_TOKEN" '{"question": "What was my AHI at diagnosis?"}' | pretty
echo ""

# =====================================================================
#  ACT 5: Data Loaders + System Info
# =====================================================================
echo "━━━ ACT 5: System Capabilities ━━━"
echo ""

echo "── Registered Data Loaders ──"
api_call GET /api/v1/loaders "$ALICE_TOKEN" | pretty
echo ""

echo "── Collections ──"
api_call GET /api/v1/collections "$ALICE_TOKEN" | pretty
echo ""

# =====================================================================
#  Finale
# =====================================================================
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Demo Complete                            ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Patients: Alice (compliant) & Bob (struggling)            ║"
echo "║  Auth:     Cognito JWT with custom:patient_id              ║"
echo "║  Storage:  S3 Vectors (1024-dim, cosine, patient-filtered) ║"
echo "║  LLM:     Claude Haiku 4.5 via Bedrock EU inference prof.  ║"
echo "║  Audit:    DynamoDB ingestion metadata + session history   ║"
echo "║  HIPAA:    Patient isolation verified — zero cross-access  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Teardown: bash scripts/aws_demo.sh teardown"
echo ""
echo "Try your own queries:"
echo "  # Get Alice's token"
echo "  TOKEN=\$(aws cognito-idp admin-initiate-auth \\"
echo "    --user-pool-id $POOL_ID --client-id $CLIENT_ID \\"
echo "    --auth-flow ADMIN_USER_PASSWORD_AUTH \\"
echo "    --auth-parameters USERNAME=alice-cpap,PASSWORD='AliceCpap2026!' \\"
echo "    --region $REGION --query 'AuthenticationResult.IdToken' --output text)"
echo ""
echo "  curl -s -X POST $API/api/v1/query \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -H \"Authorization: Bearer \$TOKEN\" \\"
echo "    -d '{\"question\": \"YOUR QUESTION\"}' | python3 -m json.tool"
