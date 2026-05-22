"""OAuth crypto utilities — mirrors src/services/oauth/crypto.ts."""
from __future__ import annotations

import base64
import hashlib
import os


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def generateCodeVerifier() -> str:
    """Generate a PKCE code verifier.

    Mirrors generateCodeVerifier() from crypto.ts.
    """
    return _base64url_encode(os.urandom(32))


def generateCodeChallenge(verifier: str) -> str:
    """Generate a PKCE code challenge from a verifier.

    Mirrors generateCodeChallenge() from crypto.ts.
    """
    digest = hashlib.sha256(verifier.encode()).digest()
    return _base64url_encode(digest)


def generateState() -> str:
    """Generate a random state parameter for OAuth CSRF protection.

    Mirrors generateState() from crypto.ts.
    """
    return _base64url_encode(os.urandom(32))


generate_code_verifier = generateCodeVerifier
generate_code_challenge = generateCodeChallenge
generate_state = generateState
