# MoSCoW Categorization

## Must Have (Core - ship or fail)

- [x] FastAPI application with Mangum adapter
- [x] Health check endpoint (`GET /health`)
- [x] Query endpoint (`POST /api/v1/query`)
- [x] Pluggable vector backend interface (BaseVectorDB)
- [x] ChromaDB vector backend (local dev)
- [x] S3 Vectors vector backend (production)
- [x] Patient isolation middleware (mandatory patient_id filter from JWT)
- [x] PHI redaction parser (Comprehend Medical interface, regex fallback)
- [x] Hybrid retriever (vector + BM25 merge + dedup)
- [x] Simple reranker (token overlap scoring)
- [x] LLM generator (Bedrock Haiku 4.5 + Anthropic direct fallback)
- [x] Guardrails pipeline (PHI redaction, denied-topic checks, grounding; disclaimer appended in API response layer)
- [x] Docker Compose (FastAPI + ChromaDB)
- [x] Pydantic request/response models at API boundaries
- [x] Unit tests (34 tests, HIPAA control verification)

## Should Have (Important, not critical)

- [x] Cognita-inspired base interfaces (BaseEmbedder, BaseReranker, BaseGenerator)
- [x] BM25 keyword retriever with rank-bm25
- [x] Bedrock Titan Embedder (production)
- [x] Local dev embedder (sentence-transformers, zero AWS cost)
- [x] RAGAS-style evaluation pipeline (custom golden-set evaluation script)
- [x] Golden test set (15 Q&A pairs with ground truth)
- [x] DynamoDB metadata store (session context, patient metadata)
- [x] structlog added as dependency (structured logging integration pending)
- [x] Patient isolation integration test
- [x] Unified Dockerfile (multi-stage: local + lambda targets)
- [x] Default deps + dependency groups (local + dev)
- [x] Env profiles (.env.local + .env.aws.example)
- [ ] Registry-based polymorphism (decorator self-registration) — using factory functions instead
- [x] DynamoDB corpus backend for BM25 on S3 Vectors path
- [ ] Cohere Rerank via Bedrock (currently SimpleReranker)

## Could Have (Nice to have)

- [x] Sample ingestion script (`make ingest-samples`)
- [ ] HealthKit data loader (real-time streaming)
- [ ] FHIR R4 data loader (HealthLake interface)
- [ ] Semantic chunker (medical clause-boundary aware)
- [ ] Config-driven model gateway (models_config.yaml)
- [ ] OpenSearch Serverless backend (IaC only)
- [ ] Prompt caching configuration
- [ ] WebSocket API Gateway for streaming responses (ADR-004)

## Won't Have (Out of scope for MVP)

- [ ] EHR/HL7v2 data loader (complex legacy parsing)
- [ ] Multi-region active-active (DynamoDB Global Tables)
- [ ] LLM observability (LangSmith/Braintrust)
- [ ] Federated learning layer
- [ ] Agentic clinical workflow (LangGraph)
- [ ] Bedrock Knowledge Base integration
