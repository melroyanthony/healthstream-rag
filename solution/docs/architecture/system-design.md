# System Design Overview

## Scale Estimates

| Metric | Demo | Production |
|--------|------|------------|
| Daily Active Users | 1-10 (reviewers) | 10,000,000 |
| Queries/day | ~500 | 50,000,000 |
| Sustained QPS | <1 | 578 |
| Peak QPS | <1 | ~1,750 |
| Vector store size | ~10K vectors | 10B+ vectors |
| Read/Write ratio | 90:10 | 95:5 |
| Data volume | <100MB | ~500GB vectors, ~2TB structured |

**Decision**: Single server (Docker Compose) for demo; serverless Lambda for production.

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend framework | FastAPI 0.115+ (Python 3.13) | Async, Pydantic validation, Mangum for Lambda |
| Package manager | uv | Fast, deterministic, never pip |
| Vector store (prod) | Amazon S3 Vectors | GA Dec 2025, ~100ms, pay-per-query, 2B vectors/index |
| Vector store (dev) | ChromaDB | Zero cost, in-process, good DX |
| Structured data | DynamoDB on-demand | Zero idle cost, free tier, Lambda-native |
| LLM (prod) | Claude Haiku 4.5 via Bedrock | $1.00/MTok in, $5.00/MTok out |
| LLM (dev) | Anthropic direct API | Free with API key for dev |
| Embeddings (prod) | Bedrock Titan Embeddings V2 | 1024-dim, $0.0001/1K tokens |
| Embeddings (dev) | sentence-transformers (all-MiniLM-L6-v2) | 384-dim, zero cost, local |
| PHI detection | AWS Comprehend Medical | HIPAA-eligible, entity detection + redaction |
| Reranking | Cohere Rerank via Bedrock | Cross-encoder reranking |
| BM25 | rank-bm25 library | In-process keyword search |
| Auth (prod) | Amazon Cognito JWT | patient_id claim |
| Auth (dev) | Mock JWT middleware | Synthetic patient_id |
| Container | Docker Compose | FastAPI + ChromaDB for local dev |

## Patterns Selected

### Data Access
- **Repository pattern**: All data access through abstract interfaces (BaseVectorDB, BaseDataLoader)
- **Pluggable backends**: Environment variable selects implementation at startup
- **Registry pattern**: Components self-register via decorators (Cognita pattern)
- **Pagination**: Not needed for RAG queries (fixed top-K), but list endpoints paginated

### Retrieval
- **Hybrid retrieval**: Vector semantic + BM25 keyword, merged + deduplicated
- **Reranking**: Cross-encoder rerank to produce final top-5 from merged top-40
- **Patient isolation**: Mandatory metadata filter on every retrieval call

### Security
- **JWT authentication**: Patient_id extracted from JWT claims, never from user input
- **Input validation**: Pydantic models at all API boundaries
- **PHI redaction**: Mandatory pre-embedding step, cannot be bypassed
- **Guardrails**: Post-generation PHI check, grounding verification, topic restrictions

### Resilience
- **Health checks**: `/health` endpoint with dependency status
- **Retry with backoff**: tenacity for AWS API calls
- **Graceful degradation**: If reranker fails, return vector results directly
- **Structured logging**: structlog for PHI-scrubbed observability

## Trade-offs

| Decision | Choice | Alternative | Rationale |
|----------|--------|-------------|-----------|
| Consistency vs Availability | Consistency (CP) | AP | Health data must be accurate, not eventually consistent |
| Latency vs Cost | Cost-optimized (~100ms S3V) | Low-latency (~10ms OpenSearch) | LLM generation dominates latency; vector query is <5% of pipeline time |
| LangChain vs Direct | Direct boto3 calls | LangChain abstraction | Reduces HIPAA audit surface; LangChain only for RAGAS evaluation |
| Monolith vs Microservices | Modular monolith (FastAPI) | Lambda per function | Demo simplicity; Lambda packaging is the same codebase with Mangum |
| SQL vs NoSQL | DynamoDB (NoSQL) | Aurora PostgreSQL | Zero idle cost, Lambda-native, no connection pooling needed |

## Component Architecture

```
healthstream_rag/
├── api/                    # FastAPI routes + Lambda handler
│   ├── main.py             # App factory, middleware, CORS
│   ├── routes/
│   │   ├── health.py       # GET /health
│   │   ├── query.py        # POST /api/v1/query
│   │   ├── collections.py  # Collection management
│   │   └── ingest.py       # Document ingestion
│   └── lambda_handler.py   # Mangum adapter
│
├── core/                   # Base interfaces (Cognita-inspired)
│   ├── base_vector_db.py   # 9 abstract methods (6 from Cognita + 3 added: query, delete_documents, collection_count)
│   ├── base_embedder.py    # BaseEmbedder interface
│   ├── base_reranker.py    # BaseReranker interface
│   └── base_generator.py   # BaseGenerator interface
│   # Phase 2: base_parser.py, base_loader.py, registry.py
│
├── vector_db/              # Vector backend implementations
│   ├── chroma_db.py        # ChromaDB (local dev)
│   ├── s3_vectors.py       # S3 Vectors (production)
│   └── factory.py          # Backend factory from VECTOR_BACKEND env var
│
├── retrievers/             # Retrieval strategies
│   ├── vector_retriever.py
│   ├── bm25_retriever.py
│   └── hybrid_retriever.py # Merge + dedup + rerank
│
├── middleware/              # HIPAA controls
│   ├── patient_isolation.py
│   └── phi_redaction.py
│
├── generators/             # LLM generation
│   ├── bedrock_generator.py
│   ├── anthropic_generator.py
│   └── factory.py
│
├── guardrails/             # Post-generation checks
│   └── pipeline.py         # apply_guardrails(): PHI redaction + denied topics + grounding check
│
├── models/                 # Pydantic models
│   └── schemas.py          # All Pydantic models (Query, Health, Ingest, Collection)
│
├── config.py               # pydantic-settings configuration
└── embedders/
    ├── bedrock_titan.py    # Production embedder
    ├── local_embedder.py   # sentence-transformers (dev)
    └── factory.py
```

## Data Flow

### Query Path (Happy Path)
```
1. Patient sends question via POST /api/v1/query
2. JWT middleware extracts patient_id (from header or mock)
3. Query controller receives (question, patient_id)
4. Embedder converts question to vector
5. Hybrid retriever:
   a. Vector search: query_vectors(embedding, patient_id filter, k=20)
   b. BM25 search: score(query text, patient document corpus, k=20)
   c. Merge + deduplicate (up to 40 -> unique set)
6. Reranker: top-5 from merged results
7. Prompt assembly: system prompt + patient context + top-5 chunks + question
8. Generator: Claude Haiku 4.5 generates response with citations
9. Guardrails: PHI check + grounding + disclaimer
10. Return: {answer, citations[], disclaimer}
```

### Ingestion Path
```
1. Document arrives (HealthKit event, FHIR resource, or EHR file)
2. Parser extracts text (source-specific)
3. PHI redaction: Comprehend Medical removes PHI entities
4. Chunker: splits into semantic chunks (medical clause-boundary aware)
5. Embedder: converts chunks to vectors
6. Vector store: upsert with patient_id metadata
7. DynamoDB: store chunk text + metadata for BM25 corpus
```
