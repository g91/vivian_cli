"""Vivian Integration Package.

Provides the glue between vivian_cli and the running Vivian platform
(OllamaPlanner at https://vivian.d0a.net / https://api-vivian.d0a.net).

Usage — from the OllamaPlanner codebase:

    from vivian_cli.integration import VivianIntegration

    # One-time setup (call at app startup)
    VivianIntegration.configure(
        base_url="https://api-vivian.d0a.net",
        internal_api_url="http://localhost:5000",   # local OllamaPlanner URL
        api_key_env="VIVIAN_API_KEY",               # env var holding the key
    )

    # Start an AI session
    from vivian_cli.integration import create_session
    session = await create_session(user_id="...", system_prompt="...")
    reply = await session.send("Hello Vivian!")

Usage — standalone CLI:

    vivian --help
    vivian "Explain this codebase"
    vivian --model qwen3.6 --no-tui "Refactor this function"
"""

from .config import IntegrationConfig, configure, get_config
from .oauth_manager import OAuthManager, get_oauth_manager
from .session import VivianSession, create_session


class VivianIntegration:
    """Facade for configuring and accessing the Vivian integration.

    Example::

        from vivian_cli.integration import VivianIntegration

        VivianIntegration.configure(
            base_url="https://api-vivian.d0a.net",
            internal_api_url="http://localhost:5000",
        )
        config = VivianIntegration.get_config()
        oauth = VivianIntegration.get_oauth_manager()
    """

    configure = staticmethod(configure)
    get_config = staticmethod(get_config)
    get_oauth_manager = staticmethod(get_oauth_manager)


__all__ = [
    "IntegrationConfig",
    "configure",
    "get_config",
    "OAuthManager",
    "get_oauth_manager",
    "VivianSession",
    "create_session",
    "VivianIntegration",
]
