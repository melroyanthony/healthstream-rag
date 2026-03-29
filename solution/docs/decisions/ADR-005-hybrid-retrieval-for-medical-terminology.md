# ADR-005: Hybrid Retrieval for Medical Terminology

## Status
Accepted

## Context
Medical terminology has exact-match requirements that pure semantic search handles poorly:
- Drug names: "metformin" vs "biguanide" -- semantic similarity is high but clinical distinction matters
- Device identifiers: "AirSense 11 S/N 12345" -- exact match critical
- ICD-10 codes: "E11.9" -- no semantic neighbourhood, only exact match

## Decision
Use hybrid retrieval (vector semantic search + BM25 keyword search) rather than pure vector retrieval.

## Implementation
1. Retrieve top-20 via vector search filtered by `patient_id`
2. Retrieve top-20 via BM25 on same patient's document corpus
3. Normalize scores to 0..1 range (min-max per strategy)
4. Merge + deduplicate by document ID, keeping highest score
5. Rerank merged results to produce final top-5:
   - Demo: `SimpleReranker` (local query-term overlap scoring)
   - Production target: Cohere Rerank via Bedrock

### BM25 Backend
- **ChromaDB path**: `list_data_point_vectors()` fetches patient corpus from ChromaDB
- **S3 Vectors path**: BM25 auto-disabled because S3 Vectors does not natively support deterministic scan/list. A demo-only `list_data_point_vectors()` exists using random-vector queries, but is non-deterministic and unsuitable as a corpus store. Production uses DynamoDB for BM25 documents
- **OpenSearch path**: BM25 is native to OpenSearch (built-in)

## Rationale
- Hybrid retrieval improves recall for exact medical terms by 15-25% (industry benchmarks)
- rank-bm25 library is lightweight (in-process, no external service)
- Score normalization prevents BM25's unbounded scores from dominating vector similarity

## Trade-offs
- BM25 corpus must be maintained alongside vector store
- Per-patient corpus size limited to ~10K chunks for in-memory BM25
- Additional latency (~20ms) for BM25 scoring

## Consequences
- BM25 enabled by default for ChromaDB/OpenSearch backends
- Auto-disabled for S3 Vectors backend (until DynamoDB corpus store is wired)
- Retrieval quality validated via RAGAS context_precision and context_recall metrics
