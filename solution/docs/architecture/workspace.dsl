workspace "HealthStream RAG" "HIPAA-compliant RAG chatbot for personal health data" {

    model {
        # People
        patient = person "Patient" "MyAir app user with CPAP device" "Patient"
        clinician = person "Clinician" "Care provider using AirView" "Clinician"

        # External Systems
        healthkit = softwareSystem "Apple HealthKit / Google Health Connect" "Wearable health data" "External"
        ehrSystems = softwareSystem "EHR Systems" "Electronic Health Records (HL7v2, CCDA)" "External"
        fhirSources = softwareSystem "FHIR R4 Sources" "Clinical data providers" "External"

        # HealthStream RAG System
        healthstream = softwareSystem "HealthStream RAG" "HIPAA-compliant AI chatbot for personal health data" {
            # API Layer
            apiGateway = container "API Gateway" "Request routing, rate limiting, auth" "AWS API Gateway + CloudFront + WAF" "AWS"
            cognitoAuth = container "Cognito Auth" "JWT authentication (Phase 2: extract custom:patient_id claim)" "Amazon Cognito" "AWS"

            # Application Layer — Query (Phase 1: Implemented)
            queryOrchestrator = container "Query Orchestrator" "Hybrid retrieve, rerank, generate, cite" "FastAPI + Lambda (Python 3.13)" "Application" {
                queryController = component "QueryController" "Orchestrates the full RAG pipeline" "Python"
                hybridRetriever = component "HybridRetriever" "Vector + BM25 merge + dedup + score normalization" "Python"
                vectorRetriever = component "VectorRetriever" "Semantic search via BaseVectorDB interface" "Python"
                bm25Retriever = component "BM25Retriever" "Keyword search for medical terms (ChromaDB only)" "Python (rank-bm25)"
                reranker = component "SimpleReranker" "Query-document relevance scoring (Phase 2: Cohere Rerank)" "Python"
                generator = component "LLMGenerator" "Claude Haiku 4.5 generation" "Bedrock (prod) / Anthropic (dev)"
                guardrails = component "GuardrailsPipeline" "PHI check, denied topics, grounding, disclaimer" "Python"
                patientIsolation = component "get_patient_id" "FastAPI Depends() — extracts patient_id from JWT Bearer token" "Python"
            }

            # Application Layer — Ingestion (Phase 1: Generic endpoint)
            ingestionPipeline = container "Ingestion Pipeline" "Parse, redact PHI, embed, store" "FastAPI /api/v1/ingest" "Application" {
                ingestEndpoint = component "IngestEndpoint" "Generic document ingestion API" "FastAPI"
                phiRedactor = component "redact_phi()" "Regex patterns (dev) / Comprehend Medical (prod)" "Python / AWS Comprehend"
                embedder = component "Embedder" "sentence-transformers (dev) / Titan V2 (prod)" "Python / Bedrock"
                # Phase 2 components (not yet implemented):
                # healthkitLoader = component "HealthKitLoader" "Real-time health events" "Kinesis + Lambda"
                # fhirLoader = component "FHIRLoader" "FHIR R4 resources" "HealthLake + EventBridge"
                # ehrLoader = component "EHRLoader" "Legacy clinical records" "S3 + Lambda"
                # chunker = component "SemanticChunker" "Medical clause-boundary chunking" "Python"
            }

            # Data Layer
            vectorStore = container "Vector Store" "Semantic similarity search" "S3 Vectors (prod) / ChromaDB (dev)" "Database"
            dynamoDB = container "DynamoDB" "Patient docs, sessions, metadata" "Amazon DynamoDB" "Database"
            s3Storage = container "S3 Document Storage" "Raw encrypted health records" "Amazon S3" "Database"

            # Security Layer
            kms = container "KMS" "Encryption keys per data source" "AWS KMS" "AWS"
            cloudTrail = container "CloudTrail" "Audit trail for HIPAA compliance" "AWS CloudTrail" "AWS"
        }

        # Relationships - System Context
        patient -> healthstream "Asks health questions" "HTTPS/WSS"
        clinician -> healthstream "Queries patient data" "HTTPS"
        healthstream -> healthkit "Ingests health events" "Kinesis + API"
        healthstream -> ehrSystems "Batch ingests records" "SFTP/S3"
        healthstream -> fhirSources "Receives FHIR resources" "REST FHIR API"

        # Relationships - Container
        patient -> apiGateway "POST /api/v1/query" "HTTPS"
        apiGateway -> cognitoAuth "Validate JWT" "IAM"
        apiGateway -> queryOrchestrator "Invoke with patient_id" "Lambda"

        queryOrchestrator -> vectorStore "query_vectors(embedding, patient_id, k=20)" "boto3 / chromadb"
        # Phase 2: queryOrchestrator -> dynamoDB "Get patient context + BM25 corpus" "boto3"

        ingestionPipeline -> vectorStore "upsert_documents(chunks, embeddings, metadata)" "boto3 / chromadb"
        ingestionPipeline -> s3Storage "Store raw encrypted records" "boto3"

        # Phase 2: Event-driven ingestion from external sources
        # healthkit -> ingestionPipeline "Stream health events" "Kinesis"
        # fhirSources -> ingestionPipeline "FHIR R4 resources" "HealthLake EventBridge"
        # ehrSystems -> ingestionPipeline "Clinical records" "S3 PutObject"

        vectorStore -> kms "Encrypt/decrypt" "KMS API"
        dynamoDB -> kms "Encrypt/decrypt" "KMS API"
        queryOrchestrator -> cloudTrail "Audit log all queries" "CloudWatch"
    }

    views {
        systemContext healthstream "SystemContext" {
            include *
            autoLayout
        }

        container healthstream "Containers" {
            include *
            autoLayout
        }

        component queryOrchestrator "QueryComponents" {
            include *
            autoLayout
        }

        component ingestionPipeline "IngestionComponents" {
            include *
            autoLayout
        }

        styles {
            element "Person" {
                shape Person
                background #08427b
                color #ffffff
            }
            element "External" {
                background #999999
                color #ffffff
            }
            element "Application" {
                background #438dd5
                color #ffffff
            }
            element "Database" {
                shape Cylinder
                background #85bbf0
                color #000000
            }
            element "AWS" {
                background #ff9900
                color #000000
            }
        }
    }
}
