"""Anthropic direct API generator for local development."""

import logging

from app.core.base_generator import BaseGenerator

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are HealthStream, a HIPAA-compliant health data assistant.
You answer questions about the patient's personal health records.

RULES:
1. Only answer based on the provided context chunks. Never fabricate information.
2. Always cite your sources using [source_id] format.
3. If the context does not contain enough information, say so clearly.
4. Never provide medical advice, diagnoses, or treatment recommendations.
5. Never reveal PHI about other patients.
6. Keep answers concise and factual.

CONTEXT CHUNKS:
{context}

Answer the patient's question based ONLY on the context above."""


class AnthropicGenerator(BaseGenerator):
    """
    Direct Anthropic API generator for local development.

    Uses Claude Haiku 4.5 via the anthropic SDK.
    Zero AWS cost -- uses Anthropic API key directly.
    """

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20250315") -> None:
        self._model = model
        self._api_key = api_key
        self._client = None

    def _get_client(self):
        """Lazy-initialize the Anthropic client."""
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        context_chunks: list[str],
    ) -> str:
        """Generate response using Anthropic direct API."""
        context = "\n\n---\n\n".join(context_chunks) if context_chunks else "No context available."
        full_system = system_prompt or SYSTEM_PROMPT
        full_system = full_system.replace("{context}", context)

        if not self._api_key:
            return self._mock_generate(user_message, context_chunks)

        try:
            client = self._get_client()
            response = client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=full_system,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except Exception as e:
            logger.warning("Anthropic API call failed: %s. Using mock.", e)
            return self._mock_generate(user_message, context_chunks)

    def _mock_generate(self, question: str, context_chunks: list[str]) -> str:
        """Fallback mock generation when API is unavailable."""
        if not context_chunks:
            return (
                "I don't have enough information in your health records "
                "to answer that question."
            )
        snippet = context_chunks[0][:200] if context_chunks else ""
        return (
            f"Based on your health records: {snippet}... "
            "Please consult your care team for detailed medical advice."
        )

    def model_name(self) -> str:
        """Return model identifier."""
        return self._model
