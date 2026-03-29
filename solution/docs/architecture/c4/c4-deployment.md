# C4 Deployment Diagram

> How is HealthStream RAG deployed on AWS?

```mermaid
graph TB
    subgraph "AWS eu-west-1 (Ireland)"
        subgraph "Edge Layer"
            CF[CloudFront CDN]
            WAF[AWS WAF<br/>Rate limit: 100 req/s per patient_id]
        end

        subgraph "API Layer"
            APIGW[API Gateway<br/>REST + WebSocket]
            COG[Amazon Cognito<br/>JWT + patient_id claim]
        end

        subgraph "VPC - Private Subnets"
            subgraph "Compute"
                LQ[Lambda: Query Orchestrator<br/>Reserved: 2,000 concurrency]
                LI[Lambda: Ingestion Pipeline<br/>Auto-scaling]
            end

            subgraph "Data Stores"
                S3V[(S3 Vectors<br/>2B vectors/index<br/>~100ms queries)]
                DDB[(DynamoDB<br/>On-demand mode<br/>Sub-10ms reads)]
                S3[(S3 Storage<br/>SSE-KMS encrypted)]
            end

            subgraph "AI/ML Services (via PrivateLink)"
                BED[Bedrock<br/>Claude Haiku 4.5<br/>Titan Embeddings V2<br/>Cohere Rerank]
                CM[Comprehend Medical<br/>PHI Detection + Redaction]
            end
        end

        subgraph "Ingestion Sources"
            KIN[Kinesis Data Streams<br/>HealthKit events]
            HL[AWS HealthLake<br/>FHIR R4 native store]
            EB[EventBridge<br/>Change triggers]
            SQS[SQS Queue<br/>Embedding buffer]
        end

        subgraph "Observability & Compliance"
            CW[CloudWatch<br/>Metrics + Logs]
            CT[CloudTrail<br/>All API audit trail]
            KMS[KMS CMK<br/>Per-source encryption keys]
            CFG[AWS Config<br/>Compliance rules]
        end
    end

    CF --> WAF --> APIGW
    APIGW --> COG
    APIGW --> LQ
    LQ -->|PrivateLink| BED
    LQ --> S3V
    LQ --> DDB
    KIN --> LI
    HL --> EB --> LI
    LI -->|PrivateLink| CM
    LI --> SQS --> LI
    LI --> S3V
    LI --> DDB
    LI --> S3
    S3V --> KMS
    DDB --> KMS
    S3 --> KMS
    LQ --> CT
    LI --> CT

    style S3V fill:#85bbf0,color:#000
    style DDB fill:#85bbf0,color:#000
    style S3 fill:#85bbf0,color:#000
    style BED fill:#ff9900,color:#000
    style CM fill:#ff9900,color:#000
    style KMS fill:#ff9900,color:#000
    style CT fill:#ff9900,color:#000
```

## Key Deployment Decisions

| Decision | Rationale |
|----------|-----------|
| **eu-west-1 (Ireland)** | S3 Vectors GA, GDPR-friendly, low latency for EU users |
| **VPC + PrivateLink** | PHI never leaves the VPC via public internet |
| **Lambda (not ECS)** | Zero idle cost, per-query pricing matches S3 Vectors model |
| **No NAT Gateway** | Data plane uses VPC Endpoints only, no internet egress for PHI |
| **KMS CMK per source** | HealthKit, FHIR, EHR data encrypted with separate keys |
