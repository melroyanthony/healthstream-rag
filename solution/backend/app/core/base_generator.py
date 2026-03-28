"""Base LLM generator interface."""

from abc import ABC, abstractmethod


class BaseGenerator(ABC):
    """Abstract interface for LLM text generation."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_message: str,
        context_chunks: list[str],
    ) -> str:
        """Generate a response given system prompt, user message, and context."""

    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier."""
