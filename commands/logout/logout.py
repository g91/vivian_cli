"""logout command — mirrors src/commands/logout/logout.tsx.

Clear authentication and end the current session.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def _clear_auth_config_state() -> None:
    from ...utils.config import save_global_config

    def _update(current: dict) -> dict:
        updated = dict(current or {})
        updated["api_key"] = None
        updated["oauthAccount"] = None
        updated["hasCompletedOnboarding"] = False
        updated["subscriptionNoticeCount"] = 0
        updated["hasAvailableSubscription"] = False

        custom_api_key_responses = updated.get("customApiKeyResponses")
        if isinstance(custom_api_key_responses, dict) and isinstance(custom_api_key_responses.get("approved"), list):
            updated["customApiKeyResponses"] = {
                **custom_api_key_responses,
                "approved": [],
            }

        return updated

    save_global_config(_update)


async def performLogout(*, clearOnboarding: bool = False) -> None:
    from ...bridge.trustedDevice import clearTrustedDeviceToken, clearTrustedDeviceTokenCache
    from ...services.remoteManagedSettings import clearRemoteManagedSettingsCache
    from ...utils.secureStorage import getSecureStorage
    from ...utils.toolSchemaCache import clearToolSchemaCache
    from ...utils.user import resetUserCache

    try:
        from ...integration.oauth_manager import get_oauth_manager

        get_oauth_manager().clear_tokens()
    except Exception:
        pass

    try:
        getSecureStorage().update({})
    except Exception:
        pass

    try:
        clearTrustedDeviceToken()
    except Exception:
        pass

    try:
        clearTrustedDeviceTokenCache()
    except Exception:
        pass

    try:
        clearToolSchemaCache()
    except Exception:
        pass

    try:
        resetUserCache()
    except Exception:
        pass

    try:
        await clearRemoteManagedSettingsCache()
    except Exception:
        pass

    if clearOnboarding:
        try:
            _clear_auth_config_state()
        except Exception:
            pass


async def call(args: str, context: CommandContext) -> TextResult:
    """Logout from Vivian AI."""
    from ...types.command import TextResult

    del args

    try:
        if hasattr(context, "set_setting"):
            context.set_setting("api_key", None)
    except Exception:
        pass

    await performLogout(clearOnboarding=True)

    try:
        app_state = getattr(context, "app_state", None)
        if app_state and hasattr(app_state, "running"):
            app_state.running = False
    except Exception:
        pass

    return TextResult(value="Successfully logged out from your Anthropic account.")


perform_logout = performLogout
logout_cmd = call
