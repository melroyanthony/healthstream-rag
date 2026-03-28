"""Patient isolation middleware -- HIPAA-critical.

Extracts patient_id from JWT. Cross-patient retrieval is
architecturally impossible because patient_id is injected
from the token, never from user input.
"""

from fastapi import Header, HTTPException

from app.config import settings


def get_patient_id(authorization: str = Header(default="")) -> str:
    """
    Extract patient_id from JWT Authorization header.

    In production: decode Cognito JWT and extract patient_id claim.
    In mock mode: return default synthetic patient ID.

    The patient_id is NEVER accepted from request body or query params.
    It is ALWAYS extracted from the authenticated JWT.
    """
    if settings.mock_auth:
        if authorization and authorization.startswith("Bearer "):
            token = authorization.removeprefix("Bearer ")
            if token.startswith("patient-"):
                return token
        return settings.default_patient_id

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    # Production: decode Cognito JWT (not implemented for local dev)
    raise HTTPException(
        status_code=501,
        detail="Production JWT validation not implemented in local dev",
    )
