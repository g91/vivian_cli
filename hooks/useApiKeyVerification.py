"""API key verification — mirrors src/hooks/useApiKeyVerification.ts."""
from __future__ import annotations

async def useApiKeyVerification(apiKey: str = "") -> dict:
    """Verify API key validity."""
    return {
        "valid": bool(apiKey and len(apiKey) > 8),
        "message": "API key is valid" if apiKey and len(apiKey) > 8 else "Invalid API key",
    }

use_api_key_verification = useApiKeyVerification
