# HealthStream RAG

> **HIPAA-compliant RAG (Retrieval-Augmented Generation) framework** for building modular, open-source health data applications on AWS -- with pluggable vector backends including Amazon S3 Vectors (GA Dec 2025).

[![CI](https://github.com/melroyanthony/healthstream-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/melroyanthony/healthstream-rag/actions/workflows/ci.yml)
[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![AWS](https://img.shields.io/badge/AWS-S3%20Vectors%20%7C%20Bedrock%20%7C%20Lambda-orange)](https://aws.amazon.com/)
[![Built With](https://img.shields.io/badge/Built%20With-Claude%20Code-purple)](https://claude.ai/code)

---

## What Is This?

A production-grade, HIPAA-compliant RAG chatbot that lets patients query their personal health data across **Apple HealthKit**, **FHIR R4**, and **legacy EHR** systems. Designed for 10M+ daily users with $0 idle cost.

**Key differentiators:**
- **Patient isolation by design** -- `patient_id` injected from JWT, never user input
- **PHI redaction before embedding** -- raw PHI never enters the vector store
- **Pluggable backends** -- swap vector store, LLM, or embedder with one env var
- **$0 idle cost** -- S3 Vectors + Lambda + DynamoDB = pay only when queried

---

## Architecture

```mermaid
graph TB
    Patient["Patient (Health App)"] -->|HTTPS| CF["CloudFront + WAF (optional edge layer)"]
    CF -.-> APIGW["API Gateway"]
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
# Clone
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
├── problem/                      # Problem statement and context
│   ├── problem.md                # Comprehensive problem statement with ADRs
│   └── data/problem.pdf          # Original assessment PDF
│
├── solution/                     # All implementation artifacts
│   ├── backend/                  # FastAPI application
│   │   ├── app/                  # Application code
│   │   │   ├── api/              # Routes, query controller, Lambda handler
│   │   │   ├── core/             # Base interfaces (Cognita-inspired)
│   │   │   ├── vector_db/        # ChromaDB + S3 Vectors backends
│   │   │   ├── retrievers/       # Vector, BM25, hybrid retriever
│   │   │   ├── generators/       # Anthropic + Bedrock generators
│   │   │   ├── embedders/        # Local + Bedrock Titan embedders
│   │   │   ├── loaders/          # HealthKit, FHIR, EHR data loaders
│   │   │   ├── middleware/       # Patient isolation + PHI redaction
│   │   │   └── guardrails/       # PHI check, grounding, disclaimer
│   │   ├── tests/                # 34 unit tests
│   │   ├── data/                 # Sample data + 15 golden test Q&A pairs
│   │   └── scripts/              # Evaluation, ingestion, Lambda packaging
│   │
│   ├── infra/terraform/          # AWS IaC (6 modules)
│   │   └── modules/              # networking, compute, storage, security, monitoring, edge
│   │
│   ├── docs/
│   │   ├── architecture/         # System design, OpenAPI, database schema
│   │   │   ├── c4/               # 6 C4 Mermaid diagrams
│   │   │   └── workspace.dsl    # Structurizr DSL (canonical C4 source)
│   │   ├── decisions/            # 6 ADRs (001-006)
│   │   └── deployment/           # AWS deployment guide
│   │
│   ├── Makefile                  # dev, test, lint, docker, deploy, eval
│   ├── docker-compose.yml        # Local dev stack
│   └── README.md                 # Detailed solution documentation
│
├── .github/                      # CI/CD, issue templates, Copilot review config
│   ├── workflows/                # CI (tests + Docker), release (semantic versioning)
│   └── ISSUE_TEMPLATE/           # Bug, feature forms
│
├── LICENSE                       # MIT
├── CONTRIBUTING.md               # Contribution guidelines
├── SECURITY.md                   # Vulnerability disclosure policy
└── README.md                     # This file
```

---

## Technology Stack

| Layer | Local Dev | Production (AWS) |
|---|---|---|
| **API** | FastAPI + Uvicorn | Lambda + API Gateway + Cognito |
| **Vector Store** | ChromaDB | S3 Vectors |
| **LLM** | Anthropic direct API | Bedrock Claude Haiku 4.5 |
| **Embeddings** | sentence-transformers (384d) | Bedrock Titan V2 (1024d) |
| **BM25 Retrieval** | ChromaDB corpus | DynamoDB corpus |
| **PHI Redaction** | Regex patterns | AWS Comprehend Medical |
| **Auth** | Mock (Bearer token) | Cognito JWT |
| **IaC** | Docker Compose | Terraform (6 modules) |

---

## Configuration

All configuration via environment variables (see [`backend/.env.example`](solution/backend/.env.example)):

| Variable | Default | Description |
|----------|---------|-------------|
| `VECTOR_BACKEND` | `chroma` | Vector store: `chroma`, `s3vectors` |
| `LLM_BACKEND` | `anthropic` | LLM: `anthropic`, `bedrock` |
| `EMBEDDER_BACKEND` | `local` | Embedder: `local`, `bedrock` |
| `ANTHROPIC_API_KEY` | _(empty)_ | Anthropic API key (leave blank for mock) |
| `MOCK_AUTH` | `true` | Use mock JWT authentication |
| `AWS_REGION` | `eu-west-1` | AWS region for production services |

---

## Architecture Documentation

| Document | Description |
|---|---|
| [C4 Context](solution/docs/architecture/c4/c4-context.md) | System context -- patients, clinicians, data sources |
| [C4 Container](solution/docs/architecture/c4/c4-container.md) | Containers -- API GW, Query Orchestrator, data stores |
| [C4 Component: Query](solution/docs/architecture/c4/c4-component-query.md) | RAG pipeline internals |
| [C4 Component: Ingestion](solution/docs/architecture/c4/c4-component-ingestion.md) | Ingestion pipeline |
| [C4 Deployment](solution/docs/architecture/c4/c4-deployment.md) | AWS deployment topology |
| [HIPAA Controls](solution/docs/architecture/c4/hipaa-controls.md) | 4-layer defense model |
| [System Design](solution/docs/architecture/system-design.md) | Scale analysis, patterns, trade-offs |
| [OpenAPI Spec](solution/docs/architecture/openapi.yaml) | 6 endpoints, full schemas |
| [Database Schema](solution/docs/architecture/database-schema.md) | Vector store + DynamoDB tables |
| [AWS Deployment Guide](solution/docs/deployment/aws-deployment-guide.md) | Step-by-step deploy |

---

## Testing

```bash
cd solution/backend

# Unit tests (34 tests, ~5s)
MOCK_AUTH=true uv run pytest tests/ -v

# RAGAS evaluation (15 golden Q&A pairs)
MOCK_AUTH=true uv run python scripts/evaluate.py

# E2E happy path (requires running server)
bash ../scripts/test-e2e.sh
```

| Test Suite | Count | What It Validates |
|---|---|---|
| Unit tests | 34 | Health, query, ingest, collections, vector DB, patient isolation, PHI redaction, guardrails |
| RAGAS eval | 15 | Faithfulness, answer relevancy, context precision, context recall, PHI leakage (=0), patient isolation (PASS) |
| E2E | 9 | Full CRUD flow against running API |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code standards, and pull request process.

## Security

See [SECURITY.md](SECURITY.md) for vulnerability disclosure policy and HIPAA security design.

## License

[MIT](LICENSE)

---

**Melroy Anthony** -- AI Architect & Lead Software Engineer | Dublin, Ireland

Architecture designed for patient impact -- not dashboards.

*Built with [Claude Code](https://claude.ai/code) + [sdlc-claude-code-conf](https://github.com/melroyanthony/sdlc-claude-code-conf)*
