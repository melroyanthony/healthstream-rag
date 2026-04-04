# HealthStream RAG

HIPAA-compliant RAG chatbot for personal health data. Modular, open-source, AWS-native.

## Architecture

```mermaid
graph TB
    Patient["Patient (Health App)"] -->|HTTPS| API["FastAPI API Gateway"]
    API -->|JWT| Auth["Patient Isolation Middleware"]
    Auth -->|patient_id| QC["Query Controller"]

    QC --> HR["Hybrid Retriever"]
    HR --> VR["Vector Retriever"]
    HR --> BM["BM25 Retriever"]

    VR --> VDB["Vector Store"]
    BM --> VDB

    QC --> RR["Reranker"]
    QC --> GEN["LLM Generator"]
    QC --> GR["Guardrails"]

    subgraph "Vector Backends (pluggable)"
        VDB --> Chroma["ChromaDB (dev)"]
        VDB --> S3V["S3 Vectors (prod)"]
    end

    subgraph "LLM Backends (pluggable)"
        GEN --> Anthropic["Anthropic Direct (dev)"]
        GEN --> Bedrock["Bedrock Haiku 4.5 (prod)"]
    end

    subgraph "HIPAA Controls"
        PHI["PHI Redaction"]
        ISO["Patient Isolation"]
        GUARD["Guardrails Pipeline"]
    end
```

## Quick Start

### Local Development (Docker)

```bash
cd solution
docker compose up --build -d
curl http://localhost:8000/health
```

### Local Development (Manual)

```bash
cd solution/backend
uv sync

# Optional: set Anthropic API key for real LLM responses
export ANTHROPIC_API_KEY=your-key-here

# Ingest sample data
uv run python scripts/ingest_samples.py

# Start the API
uv run uvicorn app.api.main:app --reload --port 8000

# Test it
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer synthetic-patient-001" \
  -d '{"question": "What was my average sleep score last week?"}'
```

### Run Tests

```bash
cd solution/backend
uv run pytest tests/ -v
```

### Run E2E Tests

```bash
# Start the server first
cd solution/backend && uv run uvicorn app.api.main:app --port 8000 &

# Run E2E script
cd solution && bash scripts/test-e2e.sh
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check with dependency status |
| POST | `/api/v1/query` | RAG query pipeline (hybrid retrieve + rerank + generate) |
| POST | `/api/v1/ingest` | Ingest documents (parse + PHI redact + embed + store) |
| GET | `/api/v1/collections` | List vector collections |
| POST | `/api/v1/collections` | Create vector collection |
| DELETE | `/api/v1/collections/{name}` | Delete vector collection |

### Query Example

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer synthetic-patient-001" \
  -d '{"question": "What was my average sleep score last week?"}'
```

Response:
```json
{
  "answer": "Based on your health records: Your average sleep score was approximately 82/100...",
  "citations": [
    {
      "source_id": "weekly_summary_2026-03-23",
      "source_type": "healthkit",
      "text_snippet": "Weekly sleep summary: March 17-23, 2026...",
      "relevance_score": 0.85
    }
  ],
  "disclaimer": "This information is from your health records. Always consult your care team.",
  "metadata": {
    "retrieval_count": 5,
    "model": "claude-haiku-4-5-20250315",
    "latency_ms": 234.5
  }
}
```

## Project Structure

```
solution/
├── requirements/              # Stage 1: Requirements analysis
│   ├── requirements.md        # Functional + non-functional requirements
│   ├── rice-scores.md         # RICE prioritization (20 features)
│   ├── moscow.md              # MoSCoW categorization
│   └── mvp-scope.md           # MVP definition + acceptance criteria
├── docs/
│   ├── architecture/
│   │   ├── system-design.md   # Scale estimates, patterns, trade-offs
│   │   ├── openapi.yaml       # Complete API specification
│   │   ├── database-schema.md # Vector store + DynamoDB schemas
│   │   └── workspace.dsl      # C4 diagrams (Structurizr DSL)
│   └── decisions/
│       ├── ADR-001-*.md       # S3 Vectors as primary vector store
│       ├── ADR-002-*.md       # Cognita patterns, not codebase
│       └── ADR-003-*.md       # DynamoDB over Aurora
├── backend/
│   ├── app/
│   │   ├── api/               # FastAPI routes + query controller
│   │   ├── core/              # Base interfaces (Cognita-inspired)
│   │   ├── vector_db/         # ChromaDB + S3 Vectors backends
│   │   ├── retrievers/        # Vector, BM25, hybrid retriever
│   │   ├── generators/        # Anthropic + Bedrock generators
│   │   ├── embedders/         # Local + Bedrock Titan embedders
│   │   ├── middleware/        # Patient isolation + PHI redaction
│   │   ├── guardrails/        # PHI check, grounding, disclaimer
│   │   ├── models/            # Pydantic schemas
│   │   └── config.py          # pydantic-settings configuration
│   ├── tests/                 # 35 unit tests
│   ├── data/                  # Sample data + golden test set
│   └── scripts/               # Ingestion scripts
├── scripts/
│   └── test-e2e.sh            # E2E happy path test
├── infra/
│   └── terraform/             # AWS IaC (6 modules)
│       ├── main.tf            # Root module + variables
│       └── modules/
│           ├── networking/    # VPC, PrivateLink endpoints
│           ├── compute/       # Lambda, API Gateway
│           ├── storage/       # S3 Vectors, DynamoDB, S3
│           ├── security/      # KMS, Cognito, IAM
│           └── monitoring/    # CloudTrail, CloudWatch
├── checkpoints/               # Stage validation reports
├── .github/workflows/ci.yml   # CI/CD pipeline
├── docker-compose.yml         # Local dev: FastAPI backend (embedded ChromaDB)
├── README.md                  # This file
└── CHANGELOG.md
```

## Configuration

All configuration via environment variables. Copy the appropriate profile to `.env` (used by both `uv run` and `docker compose`):

```bash
cp backend/.env.local backend/.env       # Local dev
cp backend/.env.aws.example backend/.env  # AWS production
```

| Variable | Default | Description |
|----------|---------|-------------|
| `VECTOR_BACKEND` | `chroma` | Vector store: `chroma`, `s3vectors` |
| `LLM_BACKEND` | `anthropic` | LLM: `anthropic`, `bedrock` |
| `EMBEDDER_BACKEND` | `local` | Embedder: `local`, `bedrock` |
| `ANTHROPIC_API_KEY` | _(empty)_ | Anthropic API key (leave blank for mock) |
| `MOCK_AUTH` | `true` | Use mock JWT authentication |
| `AWS_REGION` | `eu-west-1` | AWS region for production services |

## Architecture Documentation

### C4 Diagrams (Mermaid — renders on GitHub)
| Level | Diagram | Description |
|-------|---------|-------------|
| L1 | [System Context](docs/architecture/c4/c4-context.md) | Patients, clinicians, external data sources |
| L2 | [Container](docs/architecture/c4/c4-container.md) | API Gateway, Query Orchestrator, Ingestion, data stores |
| L3 | [Component — Query](docs/architecture/c4/c4-component-query.md) | RAG pipeline: hybrid retrieval, reranking, guardrails |
| L3 | [Component — Ingestion](docs/architecture/c4/c4-component-ingestion.md) | Ingestion pipeline: PHI redaction, embedding (Phase 2: dedicated loaders) |
| - | [Deployment](docs/architecture/c4/c4-deployment.md) | AWS eu-west-1 topology, VPC, PrivateLink |
| - | [HIPAA Controls](docs/architecture/c4/hipaa-controls.md) | 4-layer defense model, control mapping |

**Canonical source**: [workspace.dsl](docs/architecture/workspace.dsl) (Structurizr)

### Architecture Decision Records
| ADR | Decision |
|-----|----------|
| [ADR-001](docs/decisions/ADR-001-s3-vectors-primary-vector-store.md) | S3 Vectors as primary vector store ($0 idle, ~100ms, 2B vectors) |
| [ADR-002](docs/decisions/ADR-002-cognita-patterns-not-codebase.md) | Cognita design patterns, not codebase (archived March 2026) |
| [ADR-003](docs/decisions/ADR-003-dynamodb-over-aurora-for-structured-data.md) | DynamoDB over Aurora (zero idle cost, Lambda-native) |
| [ADR-004](docs/decisions/ADR-004-async-queue-pattern-for-bedrock.md) | Async queue pattern for Bedrock at >500 sustained QPS |
| [ADR-005](docs/decisions/ADR-005-hybrid-retrieval-for-medical-terminology.md) | Hybrid retrieval (vector + BM25) for medical terminology |
| [ADR-006](docs/decisions/ADR-006-bedrock-claude-haiku-for-generation.md) | Claude Haiku 4.5 for generation ($0.0045/query) |
| [ADR-007](docs/decisions/ADR-007-lambda-inference-optimisation.md) | Lambda inference optimisation (provisioned concurrency, DLQ, context budget) |

### Other Architecture Docs
- [System Design](docs/architecture/system-design.md) — scale analysis, patterns, trade-offs
- [Database Schema](docs/architecture/database-schema.md) — vector store + DynamoDB tables
- [OpenAPI Spec](docs/architecture/openapi.yaml) — 8 endpoints, full schemas

## Key Design Decisions

1. **S3 Vectors over OpenSearch**: Pay-per-query ($0 idle) vs $345/month floor. ~100ms latency acceptable since LLM generation dominates pipeline time.

2. **Cognita patterns, not codebase**: Adopted interface contracts (BaseVectorDB, BaseEmbedder, BaseReranker, BaseGenerator). BaseParser and BaseDataLoader planned for Phase 2. Added patient isolation and PHI redaction not present in Cognita.

3. **DynamoDB over Aurora**: Zero idle cost, Lambda-native (no connection pooling), free tier covers demo.

4. **Hybrid retrieval**: Vector semantic + BM25 keyword for medical terminology exact match (drug names, ICD-10 codes, device identifiers).

## AWS Deployment (Terraform)

> **Note:** Bootstrap order for first-time deploy: (1) create ECR repo: `aws ecr create-repository --repository-name healthstream-rag --region eu-west-1`, (2) build and push a seed image: `make deploy` (will fail on Lambda update — that's expected), (3) `terraform apply -var="ecr_image_uri=..."` creates Lambda pointing at the ECR image, (4) `make deploy` again to update Lambda with the latest image.

```bash
cd solution

# Option A: Makefile (recommended — passes ecr_image_uri automatically)
make terraform-apply

# Option B: Manual terraform
cd infra/terraform
terraform init
terraform plan -var="ecr_image_uri=<ACCOUNT>.dkr.ecr.eu-west-1.amazonaws.com/healthstream-rag" -out=healthstream.plan
terraform apply healthstream.plan

# After infra is up, build + push + deploy Lambda:
# cd solution && make deploy
```

6 modules: `networking` (VPC + PrivateLink), `compute` (Lambda + API Gateway), `storage` (S3 Vectors + DynamoDB), `security` (KMS + Cognito + IAM), `monitoring` (CloudTrail + CloudWatch), `edge` (standalone WAFv2 Web ACL — attaches via CloudFront, not HTTP API directly).

## Feature Parity: Local Dev vs Production

| Feature | Local Dev | Production (AWS) | Status |
|---|---|---|---|
| Vector Store | ChromaDB (in-process) | S3 Vectors (eu-west-1) | Done |
| LLM Generation | Anthropic direct API | Bedrock Claude Haiku 4.5 | Done |
| Embeddings | sentence-transformers (384d) | Bedrock Titan V2 (1024d) | Done |
| BM25 Retrieval | ChromaDB corpus | DynamoDB corpus | Done |
| Reranker | SimpleReranker (token overlap) | Cohere Rerank (Bedrock) | Phase 2 |
| PHI Redaction | Regex patterns | AWS Comprehend Medical | Done (config-driven) |
| Authentication | Mock (Bearer token = patient_id) | Cognito JWT (custom:patient_id) | Done |
| Data Loaders | Generic /api/v1/ingest endpoint | HealthKit/FHIR/EHR dedicated loaders | Phase 2 |
| Infrastructure | Docker Compose (`--target local`) | Lambda (`--target lambda`) + Terraform (6 modules) | Done |
| Packaging | Single Dockerfile, uv dependency groups | Same Dockerfile, `uv export --no-group local --no-group dev --no-hashes` | Done |

## Testing

- **35 unit tests**: Health, query, ingest, collections, vector DB, patient isolation, PHI redaction, guardrails
- **9 E2E tests**: Full CRUD flow against running API
- **HIPAA-critical**: Patient isolation verified (zero cross-patient retrieval), PHI redaction verified (SSN, phone, MRN, DOB patterns)
