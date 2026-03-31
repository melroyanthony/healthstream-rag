# RICE Scoring

Scoring criteria:
- **Reach**: 1-10 (users impacted per demo/review)
- **Impact**: 0.25 (minimal) to 3 (massive)
- **Confidence**: 50%, 80%, 100%
- **Effort**: person-hours (1, 2, 4, 8, 16)
- **Score** = (Reach x Impact x Confidence) / Effort

| # | Feature | Reach | Impact | Confidence | Effort (hrs) | Score | Priority |
|---|---------|-------|--------|------------|--------------|-------|----------|
| 1 | RAG Query Pipeline (hybrid retrieve + rerank + generate) | 10 | 3 | 100% | 8 | 3.75 | P0 |
| 2 | Patient Isolation Middleware (HIPAA-critical) | 10 | 3 | 100% | 4 | 7.50 | P0 |
| 3 | Pluggable Vector Backend (S3V/OpenSearch/Chroma) | 10 | 3 | 80% | 8 | 3.00 | P0 |
| 4 | PHI Redaction Parser (Comprehend Medical) | 10 | 3 | 100% | 4 | 7.50 | P0 |
| 5 | FastAPI with health check + query endpoint | 10 | 2 | 100% | 4 | 5.00 | P0 |
| 6 | Cognita-inspired base interfaces (BaseVectorDB, BaseParser, etc.) | 8 | 2 | 100% | 4 | 4.00 | P1 |
| 7 | BM25 Keyword Retriever | 8 | 2 | 80% | 4 | 3.20 | P1 |
| 8 | Bedrock Guardrails (PHI check + disclaimer + grounding) | 8 | 2 | 80% | 4 | 3.20 | P1 |
| 9 | HealthKit Data Loader | 6 | 1.5 | 80% | 4 | 1.80 | P2 |
| 10 | FHIR R4 Data Loader | 6 | 1.5 | 80% | 4 | 1.80 | P2 |
| 11 | EHR/HL7v2 Data Loader | 4 | 1 | 50% | 8 | 0.25 | P3 |
| 12 | RAGAS Evaluation Framework | 8 | 2 | 80% | 8 | 1.60 | P1 |
| 13 | Golden Test Set (15 Q&A pairs) | 7 | 1.5 | 100% | 2 | 5.25 | P1 |
| 14 | Docker Compose (FastAPI + ChromaDB + DynamoDB Local) | 9 | 2 | 100% | 4 | 4.50 | P0 |
| 15 | Semantic Chunker (medical clause-boundary aware) | 6 | 1.5 | 80% | 4 | 1.80 | P2 |
| 16 | Config-driven model gateway (models_config.yaml) | 5 | 1 | 80% | 2 | 2.00 | P2 |
| 17 | DynamoDB metadata store | 7 | 1.5 | 80% | 4 | 2.10 | P1 |
| 18 | Bedrock Titan Embedder | 7 | 2 | 80% | 4 | 2.80 | P1 |
| 19 | Local dev embedder (sentence-transformers) | 8 | 1.5 | 100% | 2 | 6.00 | P1 |
| 20 | Terraform IaC (AWS deployment) | 5 | 1.5 | 50% | 16 | 0.23 | P3 |

## Priority Legend
- **P0**: Must ship - core RAG pipeline, HIPAA controls, demo infrastructure
- **P1**: Should ship - evaluation, retrieval quality, supporting components
- **P2**: Could ship - data loaders, chunker, config
- **P3**: Won't ship in MVP - IaC, EHR loader (complex, low demo value)
