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
            cognitoAuth = container "Cognito Auth" "JWT authentication with patient_id claim" "Amazon Cognito" "AWS"

            # Application Layer
            queryOrchestrator = container "Query Orchestrator" "Hybrid retrieve, rerank, generate, cite" "FastAPI + Lambda (Python 3.13)" "Application" {
                queryController = component "QueryController" "Orchestrates the full RAG pipeline" "Python"
                hybridRetriever = component "HybridRetriever" "Vector + BM25 merge + dedup" "Python"
                vectorRetriever = component "VectorRetriever" "Semantic search via vector DB" "Python"
                bm25Retriever = component "BM25Retriever" "Keyword search for medical terms" "Python (rank-bm25)"
                reranker = component "CohereReranker" "Cross-encoder reranking top-5" "Bedrock Cohere"
                generator = component "LLMGenerator" "Claude Haiku 4.5 generation" "Bedrock / Anthropic"
                guardrails = component "Guardrails" "PHI check, grounding, disclaimer" "Bedrock Guardrails"
                patientIsolation = component "PatientIsolationMiddleware" "Mandatory patient_id filter" "Python"
            }

            # Ingestion Layer
            ingestionPipeline = container "Ingestion Pipeline" "Parse, redact PHI, chunk, embed, store" "Lambda + SQS" "Application" {
                healthkitLoader = component "HealthKitLoader" "Real-time health events" "Kinesis + Lambda"
                fhirLoader = component "FHIRLoader" "FHIR R4 resources" "HealthLake + EventBridge"
                ehrLoader = component "EHRLoader" "Legacy clinical records" "S3 + Lambda"
                phiRedactor = component "PHIRedactionParser" "Comprehend Medical PHI removal" "AWS Comprehend"
                chunker = component "SemanticChunker" "Medical clause-boundary chunking" "Python"
                embedder = component "Embedder" "Titan V2 / sentence-transformers" "Bedrock / Local"
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
        queryOrchestrator -> dynamoDB "Get patient context + BM25 corpus" "boto3"

        ingestionPipeline -> vectorStore "upsert_documents(chunks, embeddings, metadata)" "boto3 / chromadb"
        ingestionPipeline -> dynamoDB "Store chunks for BM25" "boto3"
        ingestionPipeline -> s3Storage "Store raw encrypted records" "boto3"

        healthkit -> ingestionPipeline "Stream health events" "Kinesis"
        fhirSources -> ingestionPipeline "FHIR R4 resources" "HealthLake EventBridge"
        ehrSystems -> ingestionPipeline "Clinical records" "S3 PutObject"

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
