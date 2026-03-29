# ADR-002: Cognita Design Patterns, Not Cognita Codebase

## Status
Accepted

## Context

Cognita (TrueFoundry, Apache-2.0) is a well-structured open-source RAG framework with a proven modular design. It defines 5 plugin module types (dataloaders, parsers, vector_db, query_controllers, model_gateway) with a registry-based architecture. However, the codebase was archived March 13, 2026, predates S3 Vectors GA, and includes dependencies (LangChain, Prisma, Qdrant) that increase HIPAA audit surface.

## Decision

Adopt Cognita's architectural philosophy and interface contracts. Build AWS-native implementations from scratch.

## What We Adopted (Phase 1 — Implemented)

1. **BaseVectorDB interface**: Adopted 6 of Cognita's 8 abstract methods — `create_collection`, `delete_collection`, `get_collections`, `upsert_documents`, `list_data_point_vectors`, `delete_data_point_vectors`. Added 3 new: `query` (with mandatory `patient_id`), `delete_documents`, `collection_count` — totalling 9 abstract methods. Cognita's `create_collection` takes LangChain `Embeddings`; ours takes `dimension: int` (no coupling).
2. **BaseEmbedder interface**: Cognita uses LangChain `Embeddings` base class. We created our own with `embed(texts)`, `embed_query(text)`, `dimension()` — same semantics, no LangChain dependency.
3. **BaseReranker interface**: Not directly from Cognita (which uses LangChain retriever patterns). Our own `rerank(query, results, top_k)` contract.
4. **BaseGenerator interface**: Our own `generate(system_prompt, user_message, context_chunks)` contract. Cognita uses LangChain LLM chains.
5. **Indexer/Query Controller separation**: Async ingestion (POST /ingest) decoupled from synchronous query (POST /query).
6. **Config-driven backend selection**: `VECTOR_BACKEND`, `LLM_BACKEND`, `EMBEDDER_BACKEND` environment variables with factory pattern. Inspired by Cognita's `models_config.yaml` gateway pattern.

## What We Deferred to Phase 2

1. **BaseParser interface**: Cognita has `PARSER_REGISTRY` with `register_parser(name, cls)` and extension-based lookup. Not yet implemented — Phase 1 uses direct regex/Comprehend Medical redaction without a parser abstraction.
2. **BaseDataLoader interface**: Cognita has `LOADER_REGISTRY` with `register_dataloader(type, cls)` and async `load_full_data()` / `load_filtered_data()`. Not yet implemented — Phase 1 uses a generic `/api/v1/ingest` endpoint. Phase 2 adds dedicated HealthKit, FHIR, EHR loaders.
3. **Registry pattern with decorators**: Cognita uses `register_parser`, `register_dataloader`, `@query_controller` decorators for component self-registration. Not yet implemented — Phase 1 uses explicit factory functions.
4. **Incremental indexing**: Cognita uses hash-based change detection to avoid re-embedding unchanged documents. Not yet implemented.

## What We Omit (Intentionally)

- `get_vector_store` (returns LangChain `VectorStore`) — LangChain coupling is HIPAA audit risk
- `get_vector_client` (implementation leak) — violates interface abstraction
- Prisma + PostgreSQL metadata store — replaced with DynamoDB (Lambda-native)
- TrueFoundry-specific loaders — replaced with AWS-native patterns
- React UI frontend — out of scope (API-only)
- LangChain in query pipeline — used only for RAGAS evaluation, not production

## What We Add (Not in Cognita)

1. **`get_patient_id()` dependency** (FastAPI `Depends()`) — mandatory `patient_id` extraction from Bearer token on every retrieval. Cognita has zero multi-tenancy or data isolation.
2. **`redact_phi()` function** — regex patterns (dev) / Comprehend Medical (prod) entity detection before embedding. Cognita has no PII/PHI handling.
3. **`apply_guardrails()` pipeline** — PHI response redaction, denied topic blocking, grounding check. Medical disclaimer appended by QueryController (not guardrails). Cognita has no guardrails.
4. **Hybrid retrieval** — vector + BM25 with score normalization (Cognita only supports vector search)
5. **Fail-fast on misconfiguration** — Bedrock backends raise RuntimeError instead of silent fallback

## Consequences

- Clean, auditable codebase with no archived dependency risk
- HIPAA compliance built into the architecture, not bolted on
- Familiar patterns for engineers who know Cognita, but AWS-native throughout
- Phase 2 can add Cognita-style registries without architectural changes
