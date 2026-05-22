"""OAuth service index — mirrors src/services/oauth/index.ts."""
from __future__ import annotations

from typing import Any, Callable, Optional


class OAuthService:
    """OAuth service handling the OAuth 2.0 authorization code flow with PKCE.

    Mirrors OAuthService from index.ts.
    """

    def __init__(self) -> None:
        from .crypto import generateCodeVerifier
        self._code_verifier: str = generateCodeVerifier()
        self._auth_code_listener = None
        self._port: Optional[int] = None
        self._manual_auth_code_resolver: Optional[Callable] = None

    async def startOAuthFlow(
        self,
        auth_url_handler: Callable,
        options: Optional[dict] = None,
    ) -> dict:
        """Start the OAuth authorization flow.

        Mirrors startOAuthFlow() from index.ts.
        """
        options = options or {}
        from .auth_code_listener import AuthCodeListener
        from .crypto import generateCodeChallenge, generateState
        from .client import buildAuthUrl, exchangeCodeForTokens

        self._auth_code_listener = AuthCodeListener()
        self._port = await self._auth_code_listener.start()

        code_challenge = generateCodeChallenge(self._code_verifier)
        state = generateState()

        manual_url = buildAuthUrl(
            code_challenge=code_challenge,
            state=state,
            port=self._port,
            is_manual=True,
            **{k: v for k, v in options.items() if k in (
                "login_with_vivian_ai", "inference_only", "org_uuid",
                "login_hint", "login_method"
            )},
        )

        await auth_url_handler(manual_url)
        auth_code = await self._auth_code_listener.wait_for_code()
        tokens = await exchangeCodeForTokens(auth_code, self._code_verifier, self._port)
        return tokens

    def provideManualAuthorizationCode(self, code: str) -> None:
        """Provide manual authorization code.

        Mirrors provideManualAuthorizationCode() from index.ts.
        """
        if self._manual_auth_code_resolver:
            self._manual_auth_code_resolver(code)

    async def cleanup(self) -> None:
        """Cleanup OAuth service resources."""
        if self._auth_code_listener:
            await self._auth_code_listener.stop()


oauth_service = OAuthService
