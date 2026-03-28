"""Bedrock Titan Embeddings V2 for production use."""

import json
import logging

from app.core.base_embedder import BaseEmbedder

logger = logging.getLogger(__name__)


class BedrockTitanEmbedder(BaseEmbedder):
    """
    Amazon Bedrock Titan Embeddings V2.

    1024 dimensions, $0.0001/1K tokens.
    Production embedder for S3 Vectors backend.
    """

    def __init__(
        self,
        model_id: str = "amazon.titan-embed-text-v2:0",
        region: str = "eu-west-1",
    ) -> None:
        self._model_id = model_id
        self._dim = 1024
        try:
            import boto3

            self._client = boto3.client("bedrock-runtime", region_name=region)
        except Exception:
            logger.warning("Bedrock runtime client not available")
            self._client = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts via Bedrock."""
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query via Bedrock Titan V2."""
        if not self._client:
            return [0.0] * self._dim
        response = self._client.invoke_model(
            modelId=self._model_id,
            body=json.dumps({"inputText": text}),
        )
        result = json.loads(response["body"].read())
        return result["embedding"]

    def dimension(self) -> int:
        """Return embedding dimension (1024 for Titan V2)."""
        return self._dim
