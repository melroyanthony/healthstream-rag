"""DynamoDB metadata store — ingestion tracking + session history.

Two tables:
  patient-documents: ingestion metadata (what was ingested, when, from where)
  sessions: query session history (for multi-turn context)

Local dev: disabled (DynamoDB not needed for ChromaDB backend).
Production: writes alongside S3 Vectors for audit + incremental indexing.
"""

import logging
import time
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger(__name__)


class DynamoMetadataStore:
    """DynamoDB operations for ingestion metadata and session history."""

    def __init__(self, region: str = "eu-west-1") -> None:
        self._region = region
        self._enabled = settings.vector_backend == "s3vectors"
        self._client = None

        if self._enabled:
            try:
                import boto3

                self._client = boto3.resource("dynamodb", region_name=region)
                env = "demo"  # from Terraform naming convention
                self._docs_table = self._client.Table(
                    f"healthstream-{env}-patient-documents"
                )
                self._sessions_table = self._client.Table(
                    f"healthstream-{env}-sessions"
                )
                logger.info("DynamoDB metadata store initialized")
            except Exception as e:
                logger.warning("DynamoDB not available: %s", e)
                self._enabled = False

    def record_ingestion(
        self,
        patient_id: str,
        chunk_id: str,
        text: str,
        source_type: str,
        source_id: str,
        collection_name: str,
    ) -> None:
        """Record an ingested document chunk for audit + incremental indexing."""
        if not self._enabled:
            return
        try:
            self._docs_table.put_item(
                Item={
                    "patient_id": patient_id,
                    "chunk_id": chunk_id,
                    "source_type": source_type,
                    "source_id": source_id,
                    "collection_name": collection_name,
                    "text_preview": text[:500],
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception as e:
            logger.error("Failed to record ingestion in DynamoDB: %s", type(e).__name__)

    def record_query_session(
        self,
        patient_id: str,
        question: str,
        answer: str,
        citation_count: int,
        model: str,
        latency_ms: float,
    ) -> None:
        """Record a query session for audit trail + multi-turn context."""
        if not self._enabled:
            return
        try:
            self._sessions_table.put_item(
                Item={
                    "patient_id": patient_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "question": question,
                    "answer_preview": answer[:500],
                    "citation_count": citation_count,
                    "model": model,
                    "latency_ms": int(latency_ms),
                    "expires_at": int(time.time()) + (90 * 86400),  # TTL: 90 days
                }
            )
        except Exception as e:
            logger.error("Failed to record session in DynamoDB: %s", type(e).__name__)

    def get_recent_sessions(
        self, patient_id: str, limit: int = 5
    ) -> list[dict]:
        """Get recent query sessions for multi-turn context enrichment."""
        if not self._enabled:
            return []
        try:
            response = self._docs_table.query(
                TableName=self._sessions_table.table_name,
                KeyConditionExpression="patient_id = :pid",
                ExpressionAttributeValues={":pid": patient_id},
                ScanIndexForward=False,
                Limit=limit,
            )
            return response.get("Items", [])
        except Exception:
            return []
