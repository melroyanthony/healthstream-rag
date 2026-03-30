# Requirements

## Problem Summary

Build a **HIPAA-compliant, AWS-native RAG (Retrieval-Augmented Generation) chatbot** for a patient-facing health companion app. The system serves 10M+ daily active users querying personal health data across Apple HealthKit, Google Health Connect, FHIR R4, and legacy EHR systems. The architecture uses Amazon S3 Vectors (GA Dec 2025) as the primary vector store with a pluggable backend pattern inspired by Cognita's modular design.

**Primary deliverable**: Working implementation demonstrating the architecture is production-viable within a ~$2.76 AWS demo budget.

## Functional Requirements

### FR-1: RAG Query Pipeline
- Accept natural language health questions from patients
- Retrieve relevant context via hybrid search (vector semantic + BM25 keyword)
- Generate answers with citations using Claude Haiku 4.5 via Bedrock
- Auto-inject medical disclaimers on all responses
- Enforce grounding threshold (0.85) to prevent hallucination

### FR-2: Data Ingestion (Three Pipelines)
- **HealthKit/Health Connect**: Real-time streaming via Kinesis (sleep sessions, AHI, mask seal, therapy hours, myAir scores)
- **FHIR R4**: Event-driven via AWS HealthLake (Patient, Observation, Condition, MedicationRequest, CarePlan)
- **EHR/HL7v2**: Batch ingestion via S3 landing zone (legacy clinical records)

### FR-3: Pluggable Vector Backend
- S3 Vectors as primary (deployed) - ~100ms latency, pay-per-query
- OpenSearch Serverless as scale-up path (IaC only) - <10ms latency
- ChromaDB for local development (zero cost)
- Swap via single environment variable: `VECTOR_BACKEND=s3vectors|opensearch|chroma`

### FR-4: Patient Isolation (HIPAA-Critical)
- Mandatory patient_id filter on every retrieval call, injected from JWT
- Cross-patient data retrieval architecturally impossible
- Patient ID from JWT claim, never from user input

### FR-5: PHI Redaction Pipeline
- AWS Comprehend Medical for PHI entity detection before embedding
- Names, DOBs, MRNs, addresses replaced with [REDACTED_*] tokens
- Raw PHI never enters the vector store

### FR-6: Hybrid Retrieval
- Vector semantic search (top-20) filtered by patient_id
- BM25 keyword search (top-20) for medical terminology exact match
- Merge + deduplicate, rerank with Cohere Rerank to produce top-5

### FR-7: Evaluation Framework
- RAGAS metrics: faithfulness, answer relevance, context precision, context recall
- Golden test set: 15 curated Q&A pairs with ground truth
- PHI leakage detection test (must be 0)
- Patient isolation verification test

### FR-8: Bedrock Guardrails
- PHI detection and redaction on LLM output
- Topic restrictions (no dosage advice, no diagnosis, no treatment plans)
- Medical disclaimer auto-injection
- Grounding check (response grounded in retrieved context)

## Non-Functional Requirements

### NFR-1: Performance
- Pipeline P50 latency target: <3 seconds end-to-end
- S3 Vectors query: ~100ms
- Sustained QPS: 578/s, Peak QPS: ~1,750/s

### NFR-2: Security & Compliance
- HIPAA Security Rule compliance (164.312)
- Encryption at rest (KMS CMK per data source)
- Encryption in transit (TLS 1.3, PrivateLink)
- Audit trail via CloudTrail
- VPC-isolated data plane (no NAT Gateway for PHI)

### NFR-3: Cost
- Demo budget: ~$2.76 per deployment ($100 total covers ~36 deployments)
- Zero idle cost architecture (Lambda + S3 Vectors + DynamoDB on-demand)
- Production optimisations documented (target 75-80% cost reduction)

### NFR-4: Scalability
- 10M DAU, 50M daily queries
- Lambda reserved concurrency: 2,000
- SQS buffer for Bedrock at >500 sustained QPS (ADR-004)

### NFR-5: Observability
- CloudWatch metrics and logs (PHI-scrubbed)
- CloudTrail all-API logging
- AWS Config for compliance evidence
- Structured logging via structlog

## Constraints

1. **AWS-native**: All production services must be AWS managed services
2. **Python 3.13**: Using `uv` for package management (never pip)
3. **FastAPI**: With Mangum adapter for Lambda deployment
4. **No LangChain in core pipeline**: Only for evaluation (RAGAS) - reduces HIPAA audit surface
5. **EU region**: eu-west-1 (Ireland) for data residency
6. **Demo scope**: Local dev uses ChromaDB + Anthropic direct API; AWS deployment uses S3 Vectors + Bedrock
7. **Cognita patterns, not codebase**: Adopt interface contracts and modular design, not the archived codebase
