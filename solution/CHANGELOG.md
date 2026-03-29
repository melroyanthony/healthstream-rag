# Changelog

## [1.5.2](https://github.com/melroyanthony/healthstream-rag/releases/tag/v1.5.2) (2026-03-29)

### Miscellaneous

* gitignore .env.aws (AWS credentials)

## [1.5.1](https://github.com/melroyanthony/healthstream-rag/releases/tag/v1.5.1) (2026-03-29)

### Miscellaneous

* remove aws_demo.sh from tracking (contains Cognito IDs)

## [1.5.0](https://github.com/melroyanthony/healthstream-rag/releases/tag/v1.5.0) (2026-03-29)

### Features

* add idempotent AWS demo script with patient personas

## [1.4.0](https://github.com/melroyanthony/healthstream-rag/releases/tag/v1.4.0) (2026-03-29)

### Features

* Phase 2 — Haiku 4.5, BM25 via DynamoDB, data loaders, WAF, JWT decode (#24)

## [1.3.1](https://github.com/melroyanthony/healthstream-rag/releases/tag/v1.3.1) (2026-03-29)

### Documentation

* add root README.md with architecture, quick start, and doc index (#22)

## [1.3.0](https://github.com/melroyanthony/healthstream-rag/releases/tag/v1.3.0) (2026-03-29)

### Features

* add RAGAS evaluation pipeline for golden test set (#20)

## [1.2.0](https://github.com/melroyanthony/healthstream-rag/releases/tag/v1.2.0) (2026-03-29)

### Features

* add AWS deployment tooling and guide (#19)

## [1.1.1](https://github.com/melroyanthony/healthstream-rag/releases/tag/v1.1.1) (2026-03-29)

### Documentation

* fix stale architecture docs to match Phase 1 implementation (#18)

## [1.1.0](https://github.com/melroyanthony/healthstream-rag/releases/tag/v1.1.0) (2026-03-29)

### Features

* add Terraform IaC and update README with architecture index (#14)

## [1.0.2](https://github.com/melroyanthony/healthstream-rag/releases/tag/v1.0.2) (2026-03-29)

### Bug Fixes

* sort imports to pass ruff linting in CI

## [1.0.1](https://github.com/melroyanthony/healthstream-rag/releases/tag/v1.0.1) (2026-03-29)

### CI/CD

* move .github to repo root for GitHub Actions discovery

All notable changes to the HealthStream RAG project.

## [1.0.0] - 2026-03-28

### Added
- FastAPI application with health, query, collections, and ingest endpoints
- Cognita-inspired base interfaces (BaseVectorDB, BaseEmbedder, BaseGenerator, BaseReranker)
- ChromaDB vector backend for local development (384-dim, MiniLM)
- S3 Vectors vector backend for production (1024-dim, Titan V2)
- Patient isolation middleware (mandatory patient_id from JWT)
- PHI redaction parser (regex for dev, Comprehend Medical for production)
- Hybrid retriever combining vector semantic + BM25 keyword search
- Simple reranker with token overlap scoring (dev) / Cohere Rerank (prod)
- Anthropic direct API generator (dev) + Bedrock Haiku 4.5 generator (prod)
- Guardrails pipeline: PHI check, denied topic blocking, grounding verification, medical disclaimer
- Query controller orchestrating full RAG pipeline
- Docker Compose for local development
- Sample synthetic health data (2 patients, 13 documents)
- Golden test set (15 Q&A pairs with ground truth)
- 33 unit tests with full HIPAA control verification
- 9 E2E happy path tests
- OpenAPI 3.1 specification
- C4 architecture diagrams (Structurizr DSL)
- 3 Architecture Decision Records (ADRs)
- RICE scoring and MoSCoW prioritization
- GitHub Actions CI/CD pipeline

### Fixed (during Stage 4 testing)
- Guardrails early return: denied topic check was overwritten by grounding check
- MRN regex pattern: `[:\s]?` changed to `[:\s]*` for colon+space combinations
- Test isolation: used FastAPI dependency_overrides instead of settings env var mutation

### Architecture Decisions
- ADR-001: S3 Vectors as primary vector store (pay-per-query, 2B vectors/index)
- ADR-002: Cognita design patterns, not codebase (6/8 methods + patient isolation)
- ADR-003: DynamoDB over Aurora PostgreSQL (zero idle cost, Lambda-native)
