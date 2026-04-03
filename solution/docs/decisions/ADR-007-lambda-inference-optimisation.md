# ADR-007: Lambda Inference Optimisation

**Status:** Accepted
**Date:** 2026-04-03

## Context

The HealthStream RAG inference Lambda has a ~6.5s cold start (VPC ENI attach ~1.5s, container init ~1.5s, FastAPI startup ~0.5s, first Bedrock connection ~1.0s, pipeline ~2.0s). Warm invocations are ~2.1s, dominated by Bedrock LLM inference. For a healthcare chatbot, 6.5s cold start is poor UX.

## Decision

### Adopted (this PR)

1. **Provisioned Concurrency (configurable, disabled by default)** — Terraform variable `provisioned_concurrency` (default 0). Set to 2+ to keep warm containers ready, eliminating cold starts. Requires AWS account concurrency limit >12 (10 unreserved minimum + provisioned count). Cost when enabled: ~$5.80/month for 2 instances.

2. **Dead Letter Queue (SQS)** — Failed invocations route to an SQS DLQ with KMS encryption and 14-day retention. CloudWatch alarm on DLQ depth. Required for HIPAA audit trail of failures.

3. **Context Window Token Budget (3000 tokens)** — Hard-cap context tokens sent to Bedrock to prevent timeout on large documents. Rough estimate: 1 word ≈ 1.3 tokens. Chunks are already reranked (top 5), this is defense-in-depth.

4. **Lambda Alias (`live`)** — API Gateway routes to a published alias, not `$LATEST`. Required for provisioned concurrency and enables traffic shifting for future canary deployments.

### Retained (push-back on problem statement)

5. **FastAPI + Mangum retained** — The problem statement recommends removing FastAPI/Mangum for a raw handler. We retain it because:
   - ~50ms overhead (Mangum) is negligible vs ~2000ms Bedrock inference
   - 34 unit tests run against FastAPI test client
   - Pydantic validation at API boundaries (HIPAA input sanitisation)
   - OpenAPI spec auto-generated
   - Same codebase for local dev (`--target local`) and Lambda (`--target lambda`)
   - Removing it saves 50ms but breaks the entire DX and test story

6. **Haiku 4.5 over Sonnet** — Problem statement suggests Claude 3.5 Sonnet. We use Haiku 4.5 because:
   - $0.0045/query vs ~$0.015/query (3.3x cheaper)
   - RAG quality depends on retrieval, not generation model size
   - Haiku 4.5 is the latest Haiku (not retiring until well after Haiku 3)
   - Sonnet adds ~1s latency per query for marginal quality gain in RAG

7. **No LangChain** — Problem statement uses `langchain_aws`. We avoid LangChain in the query pipeline per ADR-002 (Cognita patterns, reduced audit surface). LangChain adds ~15 transitive dependencies and opaque middleware.

### Deferred to Phase 2 (documented, not implemented)

8. **Response streaming via Lambda Function URL** — Would reduce time-to-first-token from ~2s to ~800ms. Requires: new terraform resource (Function URL with `RESPONSE_STREAM`), streaming handler in Python, client-side SSE parsing. High impact but medium effort.

9. **Semantic cache (ElastiCache Redis)** — Healthcare RAG has high query repetition (formulary, ICD codes, policy). Cache hit rate estimated 40-70% at scale. Requires: ElastiCache cluster (~$12/month minimum), cache key design (hash on question template, NEVER on user context containing PHI), TTL strategy per content type. Not justified for demo scale.

10. **Split ingestion/inference Lambdas** — Currently one Lambda handles both. At >100 QPS, separate Lambdas with different concurrency/memory configs makes sense. Ingestion can be async (SQS trigger), inference needs provisioned concurrency.

11. **ECS Fargate** — Problem statement suggests Fargate + ALB for full Cognita architecture. At ~$46/month ($16 ALB + $30 Fargate) vs ~$9/month (Lambda + provisioned concurrency), Fargate is 5x the cost. Only justified at sustained >500 QPS where Lambda concurrency costs exceed Fargate.

## Cost Impact

Costs assume AWS free tier applied (consistent with deployment guide).

| Item | Before | After | Delta |
|------|--------|-------|-------|
| Lambda on-demand | < $0.01/month | < $0.01/month | $0.00 |
| Provisioned Concurrency (2 × 1024MB) | $0.00 | ~$5.80/month | +$5.80 |
| SQS DLQ | $0.00 | $0.00 (free tier) | $0.00 |
| **Total (default, no provisioned)** | **~$3.05/month** | **~$3.05/month** | **$0.00** |
| **Total (with provisioned concurrency)** | **~$3.05/month** | **~$8.85/month** | **+$5.80** |

## Consequences

- Cold starts eliminated for up to 2 concurrent requests
- Failed invocations are auditable (HIPAA compliance)
- Context overflow won't cause Bedrock timeout
- API Gateway routes to alias — enables future canary deployments
- Monthly cost increases from ~$3 to ~$9 (still under $10 demo budget)
