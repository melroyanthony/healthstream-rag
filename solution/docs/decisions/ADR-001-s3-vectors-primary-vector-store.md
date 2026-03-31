# ADR-001: S3 Vectors as Primary Vector Store

## Status
Accepted

## Context

The HealthStream RAG system requires a vector store for semantic similarity search across patient health data. Key requirements:
- HIPAA compliance (encryption, audit, IAM)
- Metadata filtering by patient_id (mandatory)
- Cost-effective for demo ($2.76 budget) and production (10M DAU)
- Scalable to billions of vectors

Options considered:
1. **Amazon S3 Vectors** (GA Dec 2025) - ~100ms latency, pay-per-query, 2B vectors/index
2. **OpenSearch Serverless** - <10ms latency, $345/month minimum idle cost
3. **Pinecone/Weaviate** - managed, but not AWS-native (HIPAA BAA complexity)
4. **ChromaDB** - excellent for local dev, not production-grade

## Decision

Use Amazon S3 Vectors as the production vector backend with ChromaDB for local development. Implement a pluggable backend interface (`BaseVectorDB`) allowing swap via `VECTOR_BACKEND` environment variable.

## Rationale

- **Cost**: $0 at idle (pay-per-query) vs $345/month floor for OpenSearch. Demo costs ~$0.50.
- **Scale**: 2B vectors/index, up to 20 trillion per bucket - exceeds 10M DAU requirements
- **Security**: Native AWS IAM, KMS encryption, VPC endpoints - same security model as S3
- **Latency**: ~100ms is acceptable because LLM generation (1-2s) dominates pipeline latency
- **Integration**: Native boto3 support, consistent with Lambda + DynamoDB architecture

## Trade-offs

- ~100ms vs <10ms latency: acceptable (vector query is <5% of total pipeline time)
- Not suitable for >500 sustained QPS without hybrid approach: OpenSearch scale-up path documented
- Newer service (GA Dec 2025): lower community knowledge vs established vector DBs

## Consequences

- OpenSearch Serverless remains in architecture as documented scale-up path
- ChromaDB used for local development (dimension: 384 with MiniLM)
- Production uses Titan V2 embeddings (dimension: 1024)
- All vector operations go through BaseVectorDB interface - backend swap is zero code changes
