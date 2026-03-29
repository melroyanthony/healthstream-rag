# C4 Level 3: Component Diagram - Ingestion Pipeline

> How does health data flow from sources to the vector store?

## Phase 1 (Implemented)

Single generic ingestion endpoint with PHI redaction and embedding.

```mermaid
C4Component
    title Ingestion Pipeline - Phase 1 (Implemented)

    Container_Boundary(ingest, "Ingestion Pipeline (FastAPI + Lambda)") {
        Component(ingest_api, "POST /api/v1/ingest", "FastAPI", "Accepts documents with text, source_type, source_id")
        Component(phi_redactor, "redact_phi()", "Regex patterns (dev) / Comprehend Medical (prod)", "Redacts common PHI patterns: SSN, phone, MRN, DOB, prefixed names")
        Component(embedder, "Embedder", "sentence-transformers (dev) / Titan V2 (prod)", "384-dim (dev) or 1024-dim (prod) embeddings")
    }

    Person(client, "API Client", "MyAir app or test script")
    ContainerDb(vector_store, "Vector Store", "ChromaDB (dev) / S3 Vectors (prod)")

    Rel(client, ingest_api, "POST documents with Bearer token", "HTTPS")
    Rel(ingest_api, phi_redactor, "Raw text -> redacted text")
    Rel(phi_redactor, embedder, "PHI-free text")
    Rel(embedder, vector_store, "Embeddings + metadata (patient_id from Bearer token)")
```

## Phase 2 (Target Architecture)

Dedicated loaders per data source with event-driven ingestion.

```mermaid
C4Component
    title Ingestion Pipeline - Phase 2 (Target)

    Container_Boundary(ingest, "Ingestion Pipeline (Lambda + SQS)") {
        Component(hk_loader, "HealthKitLoader", "Kinesis + Lambda", "Real-time: sleep sessions, AHI, mask seal, myAir scores")
        Component(fhir_loader, "FHIRLoader", "HealthLake + EventBridge", "Event-driven: Patient, Observation, Condition, MedicationRequest")
        Component(ehr_loader, "EHRLoader", "S3 + Lambda", "Batch: HL7v2 -> FHIR R4 normalization, CCD/CCDA parsing")
        Component(phi_redactor, "PHIRedactionParser", "AWS Comprehend Medical", "MANDATORY: Names, DOBs, MRNs, SSNs -> [REDACTED_*]")
        Component(chunker, "SemanticChunker", "Python", "Medical clause-boundary aware chunking")
        Component(embedder, "Embedder", "Bedrock Titan V2", "1024-dim embeddings for vector storage")
    }

    System_Ext(healthkit, "HealthKit / Health Connect")
    System_Ext(fhir, "FHIR R4 Sources")
    System_Ext(ehr, "EHR Systems")
    ContainerDb(vector_store, "Vector Store", "S3 Vectors")
    ContainerDb(dynamo, "DynamoDB", "Structured data + BM25 corpus")
    ContainerDb(s3_raw, "S3 Storage", "Raw encrypted records")

    Rel(healthkit, hk_loader, "Stream health events", "HTTPS -> Kinesis")
    Rel(fhir, fhir_loader, "FHIR R4 resources", "HealthLake -> EventBridge")
    Rel(ehr, ehr_loader, "Clinical records", "SFTP/S3 PutObject")
    Rel(hk_loader, phi_redactor, "Raw text")
    Rel(fhir_loader, phi_redactor, "Parsed FHIR text")
    Rel(ehr_loader, phi_redactor, "Normalized text")
    Rel(phi_redactor, chunker, "Redacted text (PHI-free)")
    Rel(chunker, embedder, "Text chunks")
    Rel(embedder, vector_store, "Embeddings + metadata (patient_id)")
    Rel(phi_redactor, dynamo, "Structured data for BM25")
    Rel(hk_loader, s3_raw, "Raw encrypted records")
```

## HIPAA Data Flow Guarantee (Both Phases)

```
Raw text with PHI
    |
    v
redact_phi()
    Phase 1: Regex patterns (local dev) / Comprehend Medical (when EMBEDDER_BACKEND=bedrock)
    Phase 2: Always Comprehend Medical
    - Names -> [REDACTED_NAME]
    - DOBs -> [REDACTED_DOB]
    - MRNs -> [REDACTED_MRN]
    - SSNs -> [REDACTED_SSN]
    |
    v
ONLY redacted text reaches:
    - Embedder
    - Vector Store
    - BM25 Corpus

Raw PHI stored ONLY in:
    - S3 (SSE-KMS encrypted, VPC-only access)
    - HealthLake (HIPAA BAA-covered) [Phase 2]
```
