"""Patient isolation middleware -- HIPAA-critical.

Extracts patient_id from JWT. Cross-patient retrieval is
architecturally impossible because patient_id is injected
from the token, never from user input.
"""

import base64
import json
import logging

from fastapi import Header, HTTPException

from app.config import settings

logger = logging.getLogger(__name__)


def get_patient_id(authorization: str = Header(default="")) -> str:
    """
    Extract patient_id from JWT Authorization header.

    In mock mode: use the Bearer token value directly as patient_id.
    In production: decode the Cognito JWT and extract custom:patient_id claim.

    The patient_id is NEVER accepted from request body or query params.
    It is ALWAYS extracted from the authenticated JWT.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Bearer token required",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    if settings.mock_auth:
        return token

    # Production: decode JWT and extract custom:patient_id
    # API Gateway already validated the JWT signature via Cognito authorizer.
    return _extract_patient_id_from_jwt(token)


def _extract_patient_id_from_jwt(token: str) -> str:
    """Decode JWT payload and extract custom:patient_id claim."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")

        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding
        decoded = base64.urlsafe_b64decode(payload)
        claims = json.loads(decoded)

        patient_id = claims.get("custom:patient_id")
        if not patient_id:
            patient_id = claims.get("sub")
            logger.warning(
                "custom:patient_id not in JWT claims, falling back to sub",
            )

        if not patient_id:
            raise ValueError("No patient_id or sub claim in JWT")

        return patient_id

    except Exception as e:
        logger.error("Failed to extract patient_id from JWT: %s", type(e).__name__)
        raise HTTPException(
            status_code=401,
            detail="Could not extract patient_id from JWT",
        )
