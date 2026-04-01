# C4 Level 3: Component Diagram - Query Orchestrator

> How does the RAG query pipeline work internally?

```mermaid
C4Component
    title Query Orchestrator - Component Diagram

    Container_Boundary(query_orch, "Query Orchestrator (FastAPI + Lambda)") {
        Component(patient_iso, "PatientIsolationMiddleware", "Python", "Extracts patient_id from JWT. NEVER from user input.")
        Component(query_ctrl, "QueryController", "Python", "Orchestrates retrieve -> rerank -> generate -> cite")
        Component(hybrid, "HybridRetriever", "Python", "Merges vector + BM25 with score normalization")
        Component(vector_ret, "VectorRetriever", "Python", "Semantic search via BaseVectorDB interface")
        Component(bm25_ret, "BM25Retriever", "Python (rank-bm25)", "Keyword search for medical terms")
        Component(reranker, "SimpleReranker", "Python", "Query-document relevance scoring")
        Component(generator, "LLMGenerator", "Bedrock / Anthropic", "Claude Haiku 4.5 response generation")
        Component(guardrails, "apply_guardrails()", "Python", "PHI redaction, denied topics, grounding check")
        Component(embedder, "Embedder", "Titan V2 / sentence-transformers", "Query embedding for vector search")
    }

    ContainerDb(vector_store, "Vector Store", "S3 Vectors / ChromaDB")
    ContainerDb(dynamo, "DynamoDB", "Chunk previews (BM25 corpus) + query sessions")
    Container(api_gw, "API Gateway", "AWS API Gateway")

    Rel(api_gw, patient_iso, "Request with JWT")
    Rel(patient_iso, query_ctrl, "patient_id injected")
    Rel(query_ctrl, embedder, "Embed query text")
    Rel(query_ctrl, hybrid, "Retrieve(query, patient_id, k=20)")
    Rel(hybrid, vector_ret, "Semantic search (top 20)")
    Rel(hybrid, bm25_ret, "Keyword search (top 20)")
    Rel(vector_ret, vector_store, "query_vectors(embedding, patient_id)")
    Rel(bm25_ret, dynamo, "Load patient document corpus")
    Rel(query_ctrl, reranker, "Rerank(query, merged_results, top_k=5)")
    Rel(query_ctrl, generator, "Generate(system_prompt, question, context)")
    Rel(query_ctrl, guardrails, "Apply(response, context_chunks)")
```

## Pipeline Flow

```
1. JWT -> PatientIsolationMiddleware -> extract patient_id
2. QueryController.query(question, patient_id)
   2a. Embed query via Titan V2 / sentence-transformers
   2b. HybridRetriever.retrieve()
       - VectorRetriever: semantic top-20 (patient_id filtered)
       - BM25Retriever: keyword top-20 (patient_id filtered)
       - Normalize scores (min-max to 0..1)
       - Merge + deduplicate by source_id
   2c. Reranker: score top-5 by query relevance
   2d. Generator: Claude Haiku 4.5 with [source_id] citations
   2e. Guardrails: PHI redaction, denied topics, grounding check
3. Return {answer, citations[], disclaimer, metadata}
```
