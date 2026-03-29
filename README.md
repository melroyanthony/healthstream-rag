# HealthStream RAG

> **HIPAA-compliant, AWS-native RAG chatbot** for querying personal health data across Apple HealthKit, FHIR R4, and legacy EHR systems -- with pluggable vector backends including Amazon S3 Vectors (GA Dec 2025).

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://www.python.org/)
[![AWS Region](https://img.shields.io/badge/AWS-eu--west--1-orange)](https://aws.amazon.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/Tests-33%20passing-brightgreen)]()

Built as a **ResMed Lead Software Engineer AI** take-home assessment. The primary deliverable is the architectural design. The working implementation demonstrates the architecture is production-viable.

---

## Architecture

```mermaid
graph TB
    Patient["Patient (MyAir App)"] -->|HTTPS| CF["CloudFront + WAF"]
    CF --> APIGW["API Gateway"]
    APIGW -->|Cognito JWT| Lambda["Lambda: Query Orchestrator"]

    Lambda --> HR["Hybrid Retriever"]
    HR --> VR["Vector Search (top 20)"]
    HR --> BM["BM25 Keywords (top 20)"]
    VR --> S3V["S3 Vectors / ChromaDB"]
    BM --> S3V

    Lambda --> RR["Reranker (top 5)"]
    Lambda --> LLM["Claude Haiku 4.5"]
    Lambda --> GR["Guardrails"]
    GR --> PHI["PHI Check"]
    GR --> TOPIC["Denied Topics"]
    GR --> GROUND["Grounding"]

    subgraph "HIPAA Controls (Architectural)"
        ISO["Patient Isolation<br/>patient_id from JWT, never user input"]
        REDACT["PHI Redaction<br/>Comprehend Medical before embedding"]
        AUDIT["Audit Trail<br/>CloudTrail all API calls"]
    end
```

### Key Design Decisions

| Decision | Rationale | ADR |
|---|---|---|
| S3 Vectors over OpenSearch/Qdrant | $0 idle, ~100ms latency, 2B vectors/index | [ADR-001](solution/docs/decisions/ADR-001-s3-vectors-primary-vector-store.md) |
| Cognita patterns, not codebase | Interface contracts adopted, archived codebase avoided | [ADR-002](solution/docs/decisions/ADR-002-cognita-patterns-not-codebase.md) |
| DynamoDB over Aurora | Zero idle cost, Lambda-native, free tier | [ADR-003](solution/docs/decisions/ADR-003-dynamodb-over-aurora-for-structured-data.md) |
| Async queue at >500 QPS | SQS buffer + WebSocket for Bedrock throttle prevention | [ADR-004](solution/docs/decisions/ADR-004-async-queue-pattern-for-bedrock.md) |
| Hybrid retrieval (vector + BM25) | Medical terminology needs exact match | [ADR-005](solution/docs/decisions/ADR-005-hybrid-retrieval-for-medical-terminology.md) |
| Claude Haiku 4.5 | Current model, $0.0045/query, lifecycle-aware | [ADR-006](solution/docs/decisions/ADR-006-bedrock-claude-haiku-for-generation.md) |

---

## Quick Start

```bash
# Clone and enter
git clone https://github.com/melroyanthony/healthstream-rag.git
cd healthstream-rag

# Option A: Docker (recommended)
cd solution && docker compose up --build -d
curl -s http://localhost:8000/health | python3 -m json.tool

# Option B: Local dev
cd solution/backend
uv sync
MOCK_AUTH=true uv run uvicorn app.api.main:app --reload --port 8000

# Ingest sample data + query
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer synthetic-patient-001" \
  -d '{"documents": [{"text": "Sleep session: myAir score 88, AHI 2.8", "source_type": "healthkit", "source_id": "s1"}]}'

curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer synthetic-patient-001" \
  -d '{"question": "What was my sleep score?"}'
```

---

## Repository Structure

```
healthstream-rag/
├── problem/                      # Assignment brief + original PDF
│   ├── problem.md                # Comprehensive problem statement with ADRs
│   └── data/problem.pdf          # Original ResMed assessment PDF
│
├── solution/                     # All generated artifacts
│   ├── backend/                  # FastAPI application
│   │   ├── app/                  # Application code
│   │   │   ├── api/              # Routes, query controller, Lambda handler
│   │   │   ├── core/             # Base interfaces (Cognita-inspired)
│   │   │   ├── vector_db/        # ChromaDB + S3 Vectors backends
│   │   │   ├── retrievers/       # Vector, BM25, hybrid retriever
│   │   │   ├── generators/       # Anthropic + Bedrock generators
│   │   │   ├── embedders/        # Local + Bedrock Titan embedders
│   │   │   ├── middleware/       # Patient isolation + PHI redaction
│   │   │   └── guardrails/       # PHI check, grounding, disclaimer
│   │   ├── tests/                # 33 unit tests
│   │   ├── data/                 # Sample data + 15 golden test Q&A pairs
│   │   └── scripts/              # Evaluation, ingestion, Lambda packaging
│   │
│   ├── infra/terraform/          # AWS IaC (5 modules)
│   │   └── modules/              # networking, compute, storage, security, monitoring
│   │
│   ├── docs/
│   │   ├── architecture/         # System design, OpenAPI, database schema
│   │   │   ├── c4/               # 6 C4 Mermaid diagrams
│   │   │   └── workspace.dsl     # Structurizr DSL (canonical)
│   │   ├── decisions/            # 6 ADRs (001-006)
│   │   └── deployment/           # AWS deployment guide
│   │
│   ├── Makefile                  # dev, test, lint, docker, deploy, eval
│   ├── docker-compose.yml        # Local dev stack
│   └── README.md                 # Detailed solution documentation
│
└── .github/                      # CI/CD, issue templates, Copilot review config
    ├── workflows/                # CI (tests + Docker), release (semantic versioning)
    ├── ISSUE_TEMPLATE/           # Bug, feature forms
    └── instructions/             # Copilot code review standards (OWASP + HIPAA)
```

---

## Architecture Documentation

| Document | Description |
|---|---|
| [C4 Context](solution/docs/architecture/c4/c4-context.md) | System context -- patients, clinicians, data sources |
| [C4 Container](solution/docs/architecture/c4/c4-container.md) | Containers -- API GW, Query Orchestrator, data stores |
| [C4 Component: Query](solution/docs/architecture/c4/c4-component-query.md) | RAG pipeline internals |
| [C4 Component: Ingestion](solution/docs/architecture/c4/c4-component-ingestion.md) | Phase 1 + Phase 2 ingestion |
| [C4 Deployment](solution/docs/architecture/c4/c4-deployment.md) | AWS eu-west-1 topology |
| [HIPAA Controls](solution/docs/architecture/c4/hipaa-controls.md) | 4-layer defense model |
| [System Design](solution/docs/architecture/system-design.md) | Scale analysis, patterns, trade-offs |
| [OpenAPI Spec](solution/docs/architecture/openapi.yaml) | 6 endpoints, full schemas |
| [Database Schema](solution/docs/architecture/database-schema.md) | Vector store + DynamoDB tables |
| [AWS Deployment Guide](solution/docs/deployment/aws-deployment-guide.md) | Step-by-step deploy to eu-west-1 |

---

## Testing

```bash
cd solution/backend

# Unit tests (33 tests, ~4s)
MOCK_AUTH=true uv run pytest tests/ -v

# RAGAS evaluation (15 golden Q&A pairs)
MOCK_AUTH=true uv run python scripts/evaluate.py

# E2E happy path (requires running server)
bash ../scripts/test-e2e.sh
```

| Test Suite | Count | What It Validates |
|---|---|---|
| Unit tests | 33 | Health, query, ingest, collections, vector DB, patient isolation, PHI redaction, guardrails |
| RAGAS eval | 15 | Faithfulness, answer relevancy, context precision, context recall, PHI leakage (=0), patient isolation (PASS) |
| E2E | 9 | Full CRUD flow against running API |

---

## Technology Stack

| Layer | Local Dev | Production (AWS) |
|---|---|---|
| **API** | FastAPI + Uvicorn | Lambda + API Gateway + Cognito |
| **Vector Store** | ChromaDB | S3 Vectors (eu-west-1) |
| **LLM** | Anthropic direct API | Bedrock Claude Haiku 4.5 |
| **Embeddings** | sentence-transformers (384d) | Bedrock Titan V2 (1024d) |
| **PHI Redaction** | Regex patterns | AWS Comprehend Medical |
| **Auth** | Mock (Bearer token) | Cognito JWT (Phase 2) |
| **IaC** | Docker Compose | Terraform (5 modules) |

---

## Author

**Melroy Anthony** -- AI Architect & Lead Software Engineer | Dublin, Ireland

Built for the ResMed Lead Software Engineer AI take-home assessment.
Architecture designed for patient impact -- not dashboards.
