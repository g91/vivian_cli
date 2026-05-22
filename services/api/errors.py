"""API errors — mirrors src/services/api/errors.ts."""
from __future__ import annotations

from typing import Optional


class APIError(Exception):
    """API error from the Anthropic API."""

    def __init__(
        self,
        status_code: int,
        error_body: dict,
        message: str,
        headers: Optional[dict] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.status = status_code
        self.error_body = error_body
        self.headers = headers or {}


class RateLimitError(APIError):
    """429 rate limit error."""


class AuthenticationError(APIError):
    """401 authentication error."""


class PermissionDeniedError(APIError):
    """403 permission denied error."""
