import os
import logging
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

# Define the OpenAPI security scheme: header "X-API-Key"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def require_analytics_api_key(x_api_key: str | None = Security(api_key_header)) -> None:
    """
    Optional API key guard for analytics endpoints.

    Behavior:
      - If env ANALYTICS_API_KEY is NOT set -> guard is DISABLED (open access).
      - If env ANALYTICS_API_KEY is set -> require header 'X-API-Key: <value>' or 401.
    """
    expected = os.getenv("ANALYTICS_API_KEY")
    if not expected:
        # Feature off -> allow anyone
        logging.getLogger("petmatch").info("Auth check: expected=%r got=%r", expected, x_api_key)
        return
    if not x_api_key or x_api_key != expected:
        # Raise standard 401 with our unified error shape
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )