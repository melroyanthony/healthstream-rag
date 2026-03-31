# Database Schema

## Overview

This project uses two data stores:
1. **Vector Store** (ChromaDB / S3 Vectors) - embeddings + metadata for semantic search
2. **DynamoDB** - structured data, session context, BM25 corpus (production only; not needed for local demo)

For the local dev/demo implementation, ChromaDB serves as both vector store and metadata store. DynamoDB patterns are documented for production reference.

---

## Vector Store Schema

### Collection: `default` (or custom per data source)

Each vector entry contains:

| Field | Type | Description |
|-------|------|-------------|
| id | string (UUID) | Unique chunk identifier |
| embedding | float[] (384 or 1024 dim) | Vector embedding of the text chunk |
| document | string | PHI-redacted text chunk |
| metadata.patient_id | string | **MANDATORY** - patient identifier (from JWT, hashed in prod) |
| metadata.source_type | string | "healthkit" / "fhir" / "ehr" |
| metadata.source_id | string | Original document identifier |
| metadata.chunk_index | integer | Position within source document |
| metadata.created_at | string (ISO 8601) | Ingestion timestamp |
| metadata.medical_codes | string[] | ICD-10, SNOMED codes if present |

### Indexes / Filters

- **Primary filter**: `patient_id` (mandatory on every query)
- **Secondary filters**: `source_type`, `created_at` range
- **Vector index**: HNSW (ChromaDB default) or ANN (S3 Vectors)

### ChromaDB Specifics
- Collection per data namespace
- Distance metric: cosine similarity
- Metadata filtering via `where` clause

### S3 Vectors Specifics (Production)
- Vector bucket: `healthstream-vectors-{env}`
- Index per collection: `healthstream-{collection_name}`
- Dimensions: 1024 (Titan V2)
- Metadata filter: `equals` on `patient_id` key
- Max 2 billion vectors per index

---

## DynamoDB Schema (Production Reference)

### Table: `healthstream-patient-documents`

Stores document text chunks for BM25 keyword search.

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| patient_id | S | PK | Patient identifier (hash) |
| chunk_id | S | SK | UUID matching vector store ID |
| text | S | - | PHI-redacted text chunk |
| source_type | S | - | healthkit / fhir / ehr |
| source_id | S | - | Original document ID |
| medical_codes | L | - | ICD-10 / SNOMED codes |
| created_at | S | - | ISO 8601 timestamp |

**GSI-1**: `source_type-index`
- PK: `patient_id`, SK: `source_type`
- Use: Filter patient docs by source type

**Access Patterns:**
1. Get all chunks for a patient: `PK = patient_id`
2. Get chunks by source type: `PK = patient_id, SK begins_with source_type` (via GSI)
3. Get specific chunk: `PK = patient_id, SK = chunk_id`

### Table: `healthstream-sessions`

Stores conversation history for context enrichment.

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| patient_id | S | PK | Patient identifier |
| session_id | S | SK | Session UUID |
| messages | L | - | List of {role, content, timestamp} |
| created_at | S | - | Session start time |
| ttl | N | - | Auto-expire after 24 hours |

**Access Patterns:**
1. Get recent session: `PK = patient_id, SK = session_id`
2. List patient sessions: `PK = patient_id` (sorted by SK desc)

### Table: `healthstream-collections`

Metadata about vector collections.

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| collection_name | S | PK | Collection identifier |
| dimension | N | - | Vector dimension (384 or 1024) |
| vector_count | N | - | Approximate vector count |
| created_at | S | - | Creation timestamp |
| backend | S | - | chroma / s3vectors / opensearch |

---

## Data Integrity

### Constraints
- `patient_id` is never null on any vector or document entry
- `text` field always contains PHI-redacted content (raw PHI never stored)
- `source_id` is unique within a patient's corpus
- Embeddings dimension must match collection configuration

### Consistency
- Vector store and DynamoDB are eventually consistent (async ingestion)
- Query path reads only from vector store (BM25 corpus loaded from DynamoDB in production, from vector store metadata in local dev)
- No cross-table transactions needed (patient-scoped access only)
