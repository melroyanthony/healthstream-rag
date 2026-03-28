# ADR-003: DynamoDB Over Aurora PostgreSQL for Structured Data

## Status
Accepted

## Context

The system needs structured storage for patient metadata, session context, BM25 document corpus, and FHIR structured data. Two AWS options were evaluated:

1. **Aurora PostgreSQL Serverless v2**: SQL, joins, full-text search. Minimum ~$43/month (0.5 ACU floor).
2. **DynamoDB on-demand**: NoSQL, key-value, zero idle cost, free tier (25GB + 25 WCU + 25 RCU).

## Decision

Use DynamoDB on-demand mode for all structured data storage.

## Rationale

- **Zero idle cost**: Aligns with S3 Vectors pay-per-query philosophy
- **Lambda-native**: No connection pooling needed (Aurora requires RDS Proxy)
- **Free tier**: 25GB + 25 WCU/RCU covers entire demo workload
- **Single-digit ms latency**: Consistent for key-value lookups (patient_id PK)
- **Point-in-time recovery**: HIPAA integrity control (164.312(c)(1))
- **Global Tables ready**: Future multi-region for GDPR data residency

## Trade-offs Accepted

- No SQL joins: denormalized access patterns required (acceptable for patient-scoped queries)
- No native full-text search: BM25 handled in-memory via rank-bm25 library
- Query flexibility limited to PK/SK patterns: acceptable because all queries are patient-scoped
- For local dev, BM25 corpus is stored in ChromaDB metadata (no DynamoDB Local needed for MVP)

## Consequences

- All DynamoDB table designs follow single-table or per-concern patterns
- BM25 corpus loaded from DynamoDB at query time (viable for <10K chunks per patient)
- Session context auto-expires via TTL (24 hours)
- No ORM needed - direct boto3 resource/client usage
