# C4 Level 2: Container Diagram

> What are the major building blocks of HealthStream RAG?

```mermaid
C4Container
    title HealthStream RAG - Container Diagram

    Person(patient, "Patient", "Health app user")

    System_Boundary(healthstream, "HealthStream RAG") {
        Container(api_gw, "API Gateway", "AWS API Gateway + CloudFront + WAF", "Request routing, rate limiting, auth")
        Container(cognito, "Cognito Auth", "Amazon Cognito", "JWT authentication with patient_id claim")
        Container(query_orch, "Query Orchestrator", "FastAPI + Lambda (Python 3.13)", "Hybrid retrieve, rerank, generate, cite")
        Container(ingest, "Ingestion Pipeline", "Lambda + SQS", "Parse, redact PHI, chunk, embed, store")
        ContainerDb(vector_store, "Vector Store", "S3 Vectors (prod) / ChromaDB (dev)", "Semantic similarity search")
        ContainerDb(dynamo, "DynamoDB", "Amazon DynamoDB", "Patient docs, sessions, metadata, BM25 corpus")
        ContainerDb(s3_storage, "S3 Document Storage", "Amazon S3", "Raw encrypted health records")
        Container(kms, "KMS", "AWS KMS", "Encryption keys per data source")
        Container(cloudtrail, "CloudTrail", "AWS CloudTrail", "HIPAA audit trail")
    }

    System_Ext(healthkit, "HealthKit / Health Connect", "Wearable health data")
    System_Ext(ehr, "EHR Systems", "Legacy clinical records")
    System_Ext(fhir, "FHIR R4 Sources", "Clinical data providers")

    Rel(patient, api_gw, "POST /api/v1/query", "HTTPS")
    Rel(api_gw, cognito, "Validate JWT", "IAM")
    Rel(api_gw, query_orch, "Invoke with patient_id", "Lambda")
    Rel(query_orch, vector_store, "query_vectors(embedding, patient_id, k=20)", "boto3")
    Rel(query_orch, dynamo, "Get patient context", "boto3")
    Rel(ingest, vector_store, "upsert_documents(chunks, embeddings)", "boto3")
    Rel(ingest, dynamo, "Store chunks for BM25", "boto3")
    Rel(ingest, s3_storage, "Store raw records", "boto3")
    Rel(healthkit, ingest, "Stream events", "Kinesis")
    Rel(fhir, ingest, "FHIR resources", "EventBridge")
    Rel(ehr, ingest, "Clinical records", "S3 PutObject")
    Rel(vector_store, kms, "Encrypt/decrypt", "KMS API")
    Rel(query_orch, cloudtrail, "Audit queries", "CloudWatch")
```

## Container Responsibilities

| Container | Responsibility | Scale Mechanism |
|-----------|---------------|-----------------|
| API Gateway | Auth, rate limit, routing | Managed, 10K TPS |
| Query Orchestrator | RAG pipeline execution | Lambda reserved concurrency 2,000 |
| Ingestion Pipeline | Parse, redact, embed, store | SQS + Lambda auto-scale |
| Vector Store | Semantic search | S3 Vectors: elastic, pay-per-query |
| DynamoDB | Structured data + BM25 corpus | On-demand, single-digit ms |
| S3 Storage | Raw encrypted records | Unlimited |
