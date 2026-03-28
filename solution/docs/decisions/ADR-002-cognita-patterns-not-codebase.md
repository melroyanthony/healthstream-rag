# ADR-002: Cognita Design Patterns, Not Cognita Codebase

## Status
Accepted

## Context

Cognita (TrueFoundry, Apache-2.0) is a well-structured open-source RAG framework with a proven modular design. It defines 5 plugin module types with a registry-based architecture. However, the codebase was archived March 2026, predates S3 Vectors GA, and includes dependencies (LangChain, Prisma, Qdrant) that increase HIPAA audit surface.

## Decision

Adopt Cognita's architectural philosophy and interface contracts. Build AWS-native implementations from scratch.

## What We Take

1. **BaseVectorDB interface** (6 of 8 methods): `create_collection`, `delete_collection`, `get_collections`, `upsert_documents`, `list_data_point_vectors`, `delete_data_point_vectors`
2. **Indexer/Query Controller separation**: Async ingestion decoupled from synchronous query path
3. **Registry-based polymorphism**: Components self-register via decorators
4. **Base interfaces**: BaseParser, BaseDataLoader, BaseEmbedder, BaseReranker
5. **Config-driven model gateway**: YAML-based provider abstraction

## What We Omit

- `get_vector_store` (returns LangChain VectorStore) - LangChain coupling is HIPAA audit risk
- `get_vector_client` (implementation leak) - violates interface abstraction
- Prisma + PostgreSQL metadata store - replaced with DynamoDB (Lambda-native)
- TrueFoundry-specific loaders - replaced with AWS-native (Kinesis, HealthLake, S3)
- React UI frontend - out of scope (API-only)

## What We Add (Not in Cognita)

1. **PatientIsolationMiddleware** - mandatory patient_id injection from JWT on every retrieval
2. **PHIRedactionParser** - Comprehend Medical entity detection before embedding
3. **AuditLogger** - CloudTrail-backed audit trail (HIPAA 164.312(b))
4. **Hybrid retrieval** - vector + BM25 (Cognita only supports vector search)

## Consequences

- Clean, auditable codebase with no archived dependency risk
- HIPAA compliance built into the architecture, not bolted on
- Familiar pattern for engineers who know Cognita, but AWS-native throughout
