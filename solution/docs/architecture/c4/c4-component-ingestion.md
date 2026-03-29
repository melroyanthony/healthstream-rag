# C4 Level 3: Component Diagram - Ingestion Pipeline

> How does health data flow from sources to the vector store?

```mermaid
C4Component
    title Ingestion Pipeline - Component Diagram

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

## HIPAA Data Flow Guarantee

```
Raw text with PHI
    |
    v
PHIRedactionParser (Comprehend Medical)
    - Names -> [REDACTED_NAME]
    - DOBs -> [REDACTED_DOB]
    - MRNs -> [REDACTED_MRN]
    - SSNs -> [REDACTED_SSN]
    |
    v
ONLY redacted text reaches:
    - SemanticChunker
    - Embedder
    - Vector Store
    - BM25 Corpus (DynamoDB)

Raw PHI stored ONLY in:
    - S3 (SSE-KMS encrypted, VPC-only access)
    - HealthLake (HIPAA BAA-covered)
```
