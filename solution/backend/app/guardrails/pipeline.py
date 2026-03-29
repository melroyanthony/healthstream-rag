"""Guardrails pipeline -- post-generation safety checks.

Applied to every LLM response before it reaches the patient:
1. PHI detection and redaction (defense in depth)
2. Denied topic check (no medical advice)
3. Grounding check (response must be based on context)
"""

import re

from app.config import settings

DENIED_TOPICS = [
    "medication dosage",
    "dosage advice",
    "diagnosis",
    "differential diagnosis",
    "treatment plan",
    "treatment recommendation",
]

PHI_ENTITY_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
    r"\b\d{3}-\d{3}-\d{4}\b",  # Phone
    r"\bMRN[:\s]*\d+\b",       # Medical Record Number
]


def apply_guardrails(
    response: str,
    context_chunks: list[str],
) -> tuple[str, bool]:
    """
    Apply guardrails to LLM response.

    Returns:
        Tuple of (cleaned_response, passed_checks).
    """
    cleaned = response

    cleaned = _redact_phi_in_response(cleaned)

    if _contains_denied_topic(cleaned):
        return (
            "I cannot provide medical advice on this topic. "
            "Please consult your healthcare provider."
        ), False

    if not _check_grounding(cleaned, context_chunks):
        return (
            "I could not generate a well-grounded response "
            "based on your health records. Please try rephrasing "
            "your question."
        ), False

    return cleaned, True


def _redact_phi_in_response(text: str) -> str:
    """Defense-in-depth PHI redaction on LLM output."""
    cleaned = text
    for pattern in PHI_ENTITY_PATTERNS:
        cleaned = re.sub(pattern, "[REDACTED]", cleaned)
    return cleaned


def _contains_denied_topic(text: str) -> bool:
    """Check if response contains denied medical advice topics."""
    text_lower = text.lower()
    return any(topic in text_lower for topic in DENIED_TOPICS)


def _check_grounding(response: str, context_chunks: list[str]) -> bool:
    """
    Simple grounding check.

    Verifies the response contains terms from the context.
    Production would use Bedrock Guardrails grounding API.
    """
    if not context_chunks:
        return True

    all_context = re.sub(r"[^\w\s]", "", " ".join(context_chunks).lower())
    response_words = set(re.sub(r"[^\w\s]", "", response.lower()).split())

    stop_words = {"the", "a", "an", "is", "was", "are", "were", "and", "or", "in", "on", "at",
                  "to", "for", "of", "with", "by", "from", "your", "you", "i", "my", "this",
                  "that", "it", "be", "has", "have", "had", "do", "does", "did", "not", "no",
                  "but", "if", "so", "as", "can", "will", "just", "than", "then", "now",
                  "based", "health", "records", "please", "consult", "care", "team",
                  "information", "data", "available", "shows", "according"}
    content_words = response_words - stop_words

    if not content_words:
        return True

    grounded_count = sum(1 for word in content_words if word in all_context)
    grounding_ratio = grounded_count / len(content_words) if content_words else 1.0

    return grounding_ratio >= settings.grounding_threshold
