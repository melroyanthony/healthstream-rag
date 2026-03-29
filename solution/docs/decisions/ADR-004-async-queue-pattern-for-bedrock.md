# ADR-004: Async Queue Pattern for Bedrock at Scale

## Status
Accepted

## Context
At 10M daily users x 5 queries/day / 86,400 seconds = 578 QPS sustained, peaking at 1,500-2,000 QPS during morning/evening spikes. Bedrock on-demand has service quota limits that make synchronous routing at this scale unreliable.

## Decision
When sustained QPS exceeds 500, route LLM calls through SQS buffer with async response via WebSocket API Gateway.

```
Mobile App <-> WebSocket API Gateway (connection_id)
                     |
               SQS Queue (buffer)
                     |
           Lambda (query orchestrator)
                     |
           Bedrock Claude Haiku 4.5 (async)
                     |
      API Gateway Management API -> push response to connection_id
```

## Rationale
- Prevents Bedrock throttle errors at peak
- Maintains user experience with streaming-style responses
- Decouples query ingestion from generation capacity
- Connection-based delivery (WebSocket) enables partial response streaming

## Trade-offs
- Added complexity: WebSocket connection management, SQS DLQ for failures
- Slight latency increase: SQS queueing and Lambda event source mapping latency (tunable via batch size, max batching window, long polling)
- Not needed for demo: synchronous REST is sufficient at demo QPS

## Consequences
- Demo uses synchronous REST (sufficient for review period)
- Production activates WebSocket + SQS when QPS exceeds 500 sustained
- Architecture supports both paths via configuration
