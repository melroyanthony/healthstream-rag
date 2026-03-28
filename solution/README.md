# HealthStream RAG

HIPAA-compliant RAG chatbot for personal health data. Built as a ResMed Lead Software Engineer AI assessment submission.

## Architecture

```mermaid
graph TB
    Patient["Patient (MyAir App)"] -->|HTTPS| API["FastAPI API Gateway"]
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
  "answer": "Based on your health records: Your average myAir score was approximately 82/100...",
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
│   ├── tests/                 # 33 unit tests
│   ├── data/                  # Sample data + golden test set
│   └── scripts/               # Ingestion scripts
├── scripts/
│   └── test-e2e.sh            # E2E happy path test
├── checkpoints/               # Stage validation reports
├── .github/workflows/ci.yml   # CI/CD pipeline
├── docker-compose.yml         # Local dev: FastAPI backend (embedded ChromaDB)
├── README.md                  # This file
└── CHANGELOG.md
```

## Configuration

All configuration via environment variables (see `backend/.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `VECTOR_BACKEND` | `chroma` | Vector store: `chroma`, `s3vectors` |
| `LLM_BACKEND` | `anthropic` | LLM: `anthropic`, `bedrock` |
| `EMBEDDER_BACKEND` | `local` | Embedder: `local`, `bedrock` |
| `ANTHROPIC_API_KEY` | _(empty)_ | Anthropic API key (leave blank for mock) |
| `MOCK_AUTH` | `true` | Use mock JWT authentication |
| `AWS_REGION` | `eu-west-1` | AWS region for production services |

## Key Design Decisions

1. **S3 Vectors over OpenSearch**: Pay-per-query ($0 idle) vs $345/month floor. ~100ms latency acceptable since LLM generation dominates pipeline time.

2. **Cognita patterns, not codebase**: Adopted interface contracts (BaseVectorDB, BaseParser) and registry pattern. Built AWS-native implementations. Added patient isolation and PHI redaction not present in Cognita.

3. **DynamoDB over Aurora**: Zero idle cost, Lambda-native (no connection pooling), free tier covers demo.

4. **Hybrid retrieval**: Vector semantic + BM25 keyword for medical terminology exact match (drug names, ICD-10 codes, device identifiers).

## Testing

- **33 unit tests**: Health, query, ingest, collections, vector DB, patient isolation, PHI redaction, guardrails
- **9 E2E tests**: Full CRUD flow against running API
- **HIPAA-critical**: Patient isolation verified (zero cross-patient retrieval), PHI redaction verified (SSN, phone, MRN, DOB patterns)
