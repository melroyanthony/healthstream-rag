# ADR-006: Bedrock Claude Haiku 4.5 for Generation

## Status
Accepted

## Context
The RAG pipeline needs a generation model that balances cost, latency, and quality for health data queries. Model lifecycle management is critical -- Claude 3 Haiku retires April 20, 2026.

## Decision
Use Claude Haiku 4.5 on Amazon Bedrock for response generation.

### Model Lifecycle (March 2026)
| Model | Status | Pricing (MTok) |
|---|---|---|
| Claude 3 Haiku | Retiring Apr 20, 2026 | $0.25 / $1.25 |
| Claude 3.5 Haiku | Retired Feb 19, 2026 | N/A |
| **Claude Haiku 4.5** | **Active (current)** | **$1.00 / $5.00** |

### Cost Analysis
- Average RAG query: ~2,000 input tokens + ~500 output tokens
- Cost per query: $0.002 + $0.0025 = **$0.0045/query**
- Demo budget ($100): ~22,000 queries (sufficient)
- Production (10M DAU, 50M queries/day): ~$225,000/day baseline

### Production Optimizations (documented, not in demo)
- Bedrock Intelligent Prompt Routing: ~30% reduction (simple -> Haiku, complex -> Sonnet)
- Prompt caching for system prompt: -60-90% on repeated context
- Batch inference for non-urgent: -50%
- Combined target: ~$45,000-$60,000/day (75-80% reduction)

## Rationale
- Claude Haiku 4.5 is the current active model on Bedrock
- Lowest latency Claude model -- critical for RAG pipeline P50 <3s target
- Bedrock provides HIPAA BAA coverage, PrivateLink, and Guardrails integration
- Direct Anthropic API used for local dev (zero AWS cost)

## Trade-offs
- 4x price increase from Claude 3 Haiku ($0.25 -> $1.00/MTok input)
- At scale, Provisioned Throughput becomes more cost-effective than on-demand
- Claude Sonnet 4 available for complex clinical reasoning (via Intelligent Prompt Routing)

## Consequences
- Demo uses Anthropic direct API (local dev, mock mode)
- Production uses Bedrock with Claude Haiku 4.5
- Model ID configurable via `BEDROCK_LLM_MODEL` environment variable
- Upgrade path to newer models requires only config change
