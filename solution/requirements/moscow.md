# MoSCoW Categorization

## Must Have (Core - ship or fail)

- [x] FastAPI application with Mangum adapter
- [x] Health check endpoint (`GET /health`)
- [x] Query endpoint (`POST /api/v1/query`)
- [x] Pluggable vector backend interface (BaseVectorDB)
- [x] ChromaDB vector backend (local dev)
- [x] S3 Vectors vector backend (production, mock-able)
- [x] Patient isolation middleware (mandatory patient_id filter from JWT)
- [x] PHI redaction parser (Comprehend Medical interface, mock-able)
- [x] Hybrid retriever (vector + BM25 merge + dedup)
- [x] Cohere reranker interface (Bedrock, mock-able)
- [x] LLM generator (Bedrock Haiku + Anthropic direct fallback)
- [x] Bedrock guardrails (PHI check, disclaimer, grounding)
- [x] Docker Compose (FastAPI + ChromaDB)
- [x] Pydantic request/response models at API boundaries
- [x] Unit tests with moto/mocks for AWS services

## Should Have (Important, not critical)

- [ ] Cognita-inspired base interfaces (BaseParser, BaseEmbedder, BaseReranker, BaseGenerator)
- [ ] Registry-based polymorphism (decorator self-registration)
- [ ] BM25 retriever with DynamoDB patient corpus
- [ ] Bedrock Titan Embedder (production)
- [ ] Local dev embedder (sentence-transformers, zero AWS cost)
- [ ] RAGAS evaluation framework integration
- [ ] Golden test set (15 Q&A pairs with ground truth)
- [ ] DynamoDB metadata store (session context, patient metadata)
- [ ] Structured logging (structlog)
- [ ] Patient isolation integration test

## Could Have (Nice to have)

- [ ] HealthKit data loader (real-time streaming mock)
- [ ] FHIR R4 data loader (HealthLake interface)
- [ ] Semantic chunker (medical clause-boundary aware)
- [ ] Config-driven model gateway (models_config.yaml)
- [ ] Sample ingestion script (`make ingest-samples`)
- [ ] OpenSearch Serverless backend (IaC only)
- [ ] Prompt caching configuration
- [ ] WebSocket API Gateway for streaming responses (ADR-004)

## Won't Have (Out of scope for MVP)

- [ ] EHR/HL7v2 data loader (complex legacy parsing)
- [ ] Terraform IaC for full AWS deployment
- [ ] Multi-region active-active (DynamoDB Global Tables)
- [ ] LLM observability (LangSmith/Braintrust)
- [ ] Federated learning layer
- [ ] Agentic clinical workflow (LangGraph)
- [ ] Bedrock Knowledge Base integration
- [ ] Production CloudFront + WAF configuration
- [ ] Cognito user pool setup
- [ ] Full CI/CD pipeline for AWS deployment
