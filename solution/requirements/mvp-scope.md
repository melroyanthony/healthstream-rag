# MVP Scope

## Goal

Deliver a working HIPAA-compliant RAG chatbot that demonstrates the full query pipeline locally (ChromaDB + Anthropic direct API) with production-ready interfaces for AWS services (S3 Vectors, Bedrock, Comprehend Medical). The implementation proves the architecture is viable within the demo budget.

## Included Features

### Core RAG Pipeline
1. **Query Endpoint** (`POST /api/v1/query`) - accepts natural language question + patient JWT
2. **Hybrid Retrieval** - vector semantic (ChromaDB/S3 Vectors) + BM25 keyword search
3. **Reranking** - Cohere Rerank via Bedrock (mock-able for local dev)
4. **Generation** - Claude Haiku 4.5 via Bedrock or Anthropic direct API
5. **Citations** - every response includes source document references
6. **Medical Disclaimer** - auto-injected on all responses

### HIPAA Security Controls
7. **Patient Isolation Middleware** - mandatory patient_id from JWT on every query
8. **PHI Redaction** - Comprehend Medical interface (mock for local dev)
9. **Bedrock Guardrails** - PHI detection, topic restrictions, grounding check
10. **Input Validation** - Pydantic models at all API boundaries

### Pluggable Architecture (Cognita-Inspired)
11. **BaseVectorDB** interface with 6 abstract methods
12. **ChromaDB backend** (local dev, zero cost)
13. **S3 Vectors backend** (production, testable with mocks)
14. **Registry-based component selection** via environment variables

### Infrastructure
15. **Docker Compose** - FastAPI + ChromaDB (+ optional DynamoDB Local)
16. **Health check** (`GET /health`) with dependency status
17. **Sample data ingestion** - synthetic health records (no real PHI)

### Testing & Evaluation
18. **Unit tests** - pytest + pytest-asyncio with moto mocks
19. **Patient isolation test** - verify zero cross-patient retrieval
20. **Golden test set** - 15 Q&A pairs with ground truth and expected citations

## Acceptance Criteria

| Criteria | Metric | Target |
|----------|--------|--------|
| Query pipeline works end-to-end | Health question returns cited answer | Pass |
| Patient isolation enforced | Cross-patient query returns 0 results | Pass |
| PHI redaction active | No PHI entities in vector store | Pass |
| Vector backend swappable | `VECTOR_BACKEND=chroma` works locally | Pass |
| Docker Compose starts cleanly | All services healthy | Pass |
| Unit tests pass | pytest green | 100% |
| API matches OpenAPI spec | All endpoints respond correctly | Pass |
| Response includes citations | Every answer has source references | Pass |
| Medical disclaimer present | Auto-injected on all responses | Pass |
| Latency acceptable | Local pipeline <5s end-to-end | Pass |

## Out of Scope

- AWS deployment (Terraform IaC documented but not executed)
- Real HealthKit/FHIR/EHR data ingestion pipelines
- Production Cognito authentication (mock JWT for demo)
- OpenSearch Serverless deployment
- Multi-region / Global Tables
- LLM observability tooling
- Agentic workflows
- Frontend UI (API-only for demo)

## Success Metrics

1. **Demo-ready**: `docker compose up` starts the full stack, query works immediately
2. **Architecture-clear**: Code structure mirrors the problem statement's module layout exactly
3. **HIPAA-provable**: Patient isolation and PHI redaction are testable and tested
4. **Evaluation-rigorous**: RAGAS metrics and golden test set demonstrate RAG quality
5. **Cost-validated**: Demo runs within $2.76 budget on AWS

## Estimated Effort

| Component | Hours |
|-----------|-------|
| Base interfaces + registry | 2 |
| Vector backends (Chroma + S3V) | 3 |
| Patient isolation + PHI redaction | 2 |
| Hybrid retriever + reranker | 3 |
| Generator + guardrails | 2 |
| Query controller (orchestrator) | 2 |
| FastAPI endpoints + models | 2 |
| Docker Compose | 1 |
| Unit tests + golden test set | 3 |
| Sample data + ingestion | 1 |
| **Total** | **21 hours** |

MVP represents ~65% of total project scope (21/32 features from RICE scoring).
