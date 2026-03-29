# HealthStream RAG — Demo Playbook

## Quick Start

```bash
cd solution/backend

# 1. Start server
uv run uvicorn app.api.main:app --reload --port 8000

# 2. Run the full demo (ingests data + runs queries)
bash scripts/demo.sh
```

## Manual Queries

### Ingest a document
```bash
curl -s -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer my-patient-id" \
  -d '{
    "documents": [{
      "text": "Your health data text here",
      "source_type": "healthkit",
      "source_id": "unique-id"
    }]
  }' | python3 -m json.tool
```

### Query health data
```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer synthetic-patient-001" \
  -d '{"question": "What was my sleep score?"}' | python3 -m json.tool
```

### Test patient isolation
```bash
# This should return 0 citations — different patient can't see your data
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer WRONG-PATIENT" \
  -d '{"question": "What was my sleep score?"}' | python3 -m json.tool
```

## Sample Patients

| Patient ID | Data | Documents |
|---|---|---|
| `synthetic-patient-001` | Sleep apnea patient with CPAP therapy | 10 docs (HealthKit + FHIR) |
| `synthetic-patient-002` | Second patient (sparse data) | 3 docs |

## Sample Questions

| Question | Expected Source | Tests |
|---|---|---|
| "What was my sleep score this week?" | HealthKit sessions | Retrieval + generation |
| "What CPAP device am I using?" | FHIR MedicationRequest | Medical device info |
| "What are my therapy goals?" | FHIR CarePlan | Goal tracking |
| "What is my AHI on therapy?" | HealthKit + FHIR Condition | Cross-source synthesis |
| "Has my mask seal improved?" | HealthKit sessions (temporal) | Trend analysis |
| "What conditions are in my health records?" | FHIR Condition | Record summary |
| "What was my leak rate on March 22?" | HealthKit session (specific date) | Exact retrieval |
| "Am I meeting my compliance goals?" | HealthKit weekly + FHIR CarePlan | Cross-source reasoning |

## Configuration (`.env`)

```bash
# Vector backend: chroma (local) | s3vectors (AWS)
VECTOR_BACKEND=chroma

# LLM: anthropic (direct API) | bedrock (AWS)
LLM_BACKEND=anthropic

# Set your Anthropic key for real LLM answers (leave blank for mock)
ANTHROPIC_API_KEY=sk-ant-...

# Auth: always true for local demo
MOCK_AUTH=true
```

## Run Evaluation

```bash
uv run python scripts/evaluate.py
```

## Docker

```bash
cd solution
docker compose up --build -d
# API at http://localhost:8000
```
