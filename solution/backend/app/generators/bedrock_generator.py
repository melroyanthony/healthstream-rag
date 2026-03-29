"""Bedrock Claude Haiku 4.5 generator for production."""

import json
import logging

from app.core.base_generator import BaseGenerator
from app.generators.anthropic_generator import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class BedrockGenerator(BaseGenerator):
    """
    Claude Haiku 4.5 via Amazon Bedrock.

    Cost: $1.00/MTok input, $5.00/MTok output.
    Average RAG query: ~$0.0045/query.
    """

    def __init__(
        self,
        model_id: str = "anthropic.claude-haiku-4-5-20251001-v1:0",
        region: str = "eu-west-1",
    ) -> None:
        self._model_id = model_id
        try:
            import boto3

            self._client = boto3.client("bedrock-runtime", region_name=region)
        except Exception:
            logger.warning("Bedrock runtime client not available")
            self._client = None

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        context_chunks: list[str],
    ) -> str:
        """Generate response via Bedrock."""
        context = "\n\n---\n\n".join(context_chunks) if context_chunks else "No context."
        full_system = (system_prompt or SYSTEM_PROMPT).replace("{context}", context)

        if not self._client:
            raise RuntimeError(
                "Bedrock runtime client unavailable. "
                "Configure AWS credentials or use LLM_BACKEND=anthropic."
            )

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "system": full_system,
            "messages": [{"role": "user", "content": user_message}],
        })

        response = self._client.invoke_model(
            modelId=self._model_id,
            body=body,
        )

        result = json.loads(response["body"].read())
        return result["content"][0]["text"]

    def model_name(self) -> str:
        """Return model identifier."""
        return self._model_id
