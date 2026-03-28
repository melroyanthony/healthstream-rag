"""PHI redaction -- mandatory before any text reaches the vector store.

In production: uses AWS Comprehend Medical for entity detection.
In local dev: uses regex-based mock redaction for common PHI patterns.
"""

import re

PHI_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]"),
    (r"\b\d{3}-\d{3}-\d{4}\b", "[REDACTED_PHONE]"),
    (r"\b(?:Name|Patient|Mr|Mrs|Ms|Dr)[:\s]+[A-Z][a-z]+ [A-Z][a-z]+\b", "[REDACTED_NAME]"),
    (r"\b\d{1,2}/\d{1,2}/\d{4}\b", "[REDACTED_DOB]"),
    (r"\b\d{1,2}-\d{1,2}-\d{4}\b", "[REDACTED_DOB]"),
    (r"\bMRN[:\s]*\d+\b", "[REDACTED_MRN]"),
    (r"\b\d+ [A-Z][a-z]+ (?:St|Ave|Rd|Blvd|Dr|Ln|Ct)\b", "[REDACTED_ADDRESS]"),
]


def redact_phi(text: str, use_comprehend: bool = False) -> str:
    """
    Redact PHI from text before embedding.

    Args:
        text: Raw text that may contain PHI.
        use_comprehend: Use AWS Comprehend Medical (production).

    Returns:
        PHI-redacted text safe for embedding and storage.
    """
    if use_comprehend:
        return _redact_with_comprehend(text)
    return _redact_with_regex(text)


def _redact_with_regex(text: str) -> str:
    """Mock PHI redaction using regex patterns for local dev."""
    redacted = text
    for pattern, replacement in PHI_PATTERNS:
        redacted = re.sub(pattern, replacement, redacted)
    return redacted


def _redact_with_comprehend(text: str) -> str:
    """Production PHI redaction using AWS Comprehend Medical."""
    import logging

    logger = logging.getLogger(__name__)
    try:
        import boto3

        client = boto3.client("comprehendmedical")
        response = client.detect_phi(Text=text)

        redacted = text
        for entity in sorted(
            response.get("Entities", []),
            key=lambda e: e["BeginOffset"],
            reverse=True,
        ):
            entity_type = entity["Type"]
            begin = entity["BeginOffset"]
            end = entity["EndOffset"]
            redacted = redacted[:begin] + f"[REDACTED_{entity_type}]" + redacted[end:]

        return redacted
    except Exception:
        logger.error(
            "Comprehend Medical failed — falling back to regex redaction. "
            "PHI may not be fully redacted. Review immediately.",
            exc_info=True,
        )
        return _redact_with_regex(text)
