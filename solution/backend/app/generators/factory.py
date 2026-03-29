"""Generator factory."""

from app.config import settings
from app.core.base_generator import BaseGenerator


def create_generator() -> BaseGenerator:
    """Create LLM generator based on LLM_BACKEND env var."""
    backend = settings.llm_backend.lower()

    if backend == "anthropic":
        from app.generators.anthropic_generator import AnthropicGenerator

        return AnthropicGenerator(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
        )

    if backend == "bedrock":
        from app.generators.bedrock_generator import BedrockGenerator

        return BedrockGenerator(
            model_id=settings.bedrock_llm_model,
            region=settings.aws_region,
        )

    raise ValueError(f"Unknown LLM backend: {backend}. Supported: anthropic, bedrock")
