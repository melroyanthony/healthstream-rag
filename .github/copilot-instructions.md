# Copilot Custom Instructions

## Repository Context

This repository is **HealthStream RAG** — a HIPAA-compliant, AWS-native RAG (Retrieval-Augmented Generation) chatbot for querying personal health data across Apple HealthKit, FHIR R4, and legacy EHR systems.

### Structure

| Directory | Contents | Notes |
|-----------|----------|-------|
| `solution/backend/app/` | FastAPI application | Cognita-inspired modular RAG architecture |
| `solution/backend/app/api/` | API routes + query controller | RAG pipeline orchestrator |
| `solution/backend/app/core/` | Base interfaces | BaseVectorDB, BaseParser, BaseEmbedder, BaseReranker |
| `solution/backend/app/vector_db/` | Vector store backends | ChromaDB (dev), S3 Vectors (prod), OpenSearch (scale-up) |
| `solution/backend/app/middleware/` | HIPAA middleware | Patient isolation + PHI redaction |
| `solution/backend/app/retrievers/` | Retrieval strategies | Hybrid (vector + BM25), semantic, keyword |
| `solution/backend/app/generators/` | LLM backends | Bedrock Haiku 4.5 (prod), Anthropic direct (dev) |
| `solution/backend/app/guardrails/` | Response guardrails | PHI check, grounding, medical disclaimer |
| `solution/backend/tests/` | pytest + RAGAS evaluation | Unit, integration, patient isolation, PHI leakage |
| `solution/docs/architecture/` | C4 diagrams, OpenAPI, ADRs | Structurizr DSL + Mermaid |
| `solution/docs/decisions/` | Architecture Decision Records | ADR-001 through ADR-007 |
| `problem/` | Assignment brief + PDF | ResMed Lead SE AI take-home |

### Key Conventions

- **Python 3.13** with `uv` package manager (never pip)
- **FastAPI** with Pydantic v2 validation at API boundaries
- **Async** for all I/O-bound operations
- **Conventional commits**: `feat(scope): description`, `fix(scope): description`
- **HIPAA controls are architectural** — patient isolation is enforced via JWT `patient_id` injection, not application logic
- **PHI redaction runs before embedding** — raw PHI never enters the vector store

### What NOT to Flag

These are intentional patterns:
- **`patient_id` injected from JWT, not from request body** — this is the HIPAA isolation mechanism
- **Separate vector DB backends with a factory pattern** — pluggable via `VECTOR_BACKEND` env var
- **BM25 in-memory scoring in Lambda** — intentional for small per-patient corpora (<10K chunks)
- **No LangChain in query pipeline** — intentional to reduce HIPAA audit surface; LangChain only used for RAGAS evaluation
- **DynamoDB instead of PostgreSQL** — zero-idle-cost serverless philosophy (see ADR-007)
