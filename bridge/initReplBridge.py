"""Port of src/bridge/initReplBridge.ts

REPL-specific wrapper around initBridgeCore. Owns the parts that read
bootstrap state — gates, cwd, session ID, git context, OAuth, title
derivation — then delegates to the bootstrap-free core.
"""
from __future__ import annotations

import re
import socket
from typing import Any, Callable, Dict, List, Optional, Set

from .bridgeConfig import getBridgeAccessToken, getBridgeBaseUrl, getBridgeTokenOverride
from .bridgeEnabled import checkBridgeMinVersion, isBridgeEnabledBlocking, isCseShimEnabled, isEnvLessBridgeEnabled
from .createSession import archiveBridgeSession, createBridgeSession, updateBridgeSessionTitle
from .debugUtils import logBridgeSkip
from .envLessBridgeConfig import checkEnvLessBridgeMinVersion
from .pollConfig import getPollIntervalConfig
from .sessionIdCompat import setCseShimGate


TITLE_MAX_LEN = 50


def _derive_title(raw: str) -> Optional[str]:
    """Quick placeholder title from raw text."""
    try:
        from ..utils.display_tags import strip_display_tags_allow_empty
        clean = strip_display_tags_allow_empty(raw)
    except Exception:
        clean = raw

    m = re.match(r"^(.*?[.!?])\s", clean)
    first_sentence = m.group(1) if m else clean
    flat = re.sub(r"\s+", " ", first_sentence).strip()
    if not flat:
        return None
    if len(flat) > TITLE_MAX_LEN:
        return flat[:TITLE_MAX_LEN - 1] + "\u2026"
    return flat


async def initReplBridge(
    on_inbound_message: Optional[Callable] = None,
    on_permission_response: Optional[Callable] = None,
    on_interrupt: Optional[Callable] = None,
    on_set_model: Optional[Callable] = None,
    on_set_max_thinking_tokens: Optional[Callable] = None,
    on_set_permission_mode: Optional[Callable] = None,
    on_state_change: Optional[Callable] = None,
    initial_messages: Optional[List[Dict[str, Any]]] = None,
    get_messages: Optional[Callable[[], List]] = None,
    previously_flushed_uuids: Optional[Set[str]] = None,
    initial_name: Optional[str] = None,
    perpetual: bool = False,
    outbound_only: bool = False,
    tags: Optional[List[str]] = None,
) -> Any:
    """Initialize the REPL bridge, returning a ReplBridgeHandle or None."""
    from ..utils.debug import log_for_debugging

    # Wire the cse_ shim kill switch
    setCseShimGate(isCseShimEnabled)

    # 1. Runtime gate
    if not await isBridgeEnabledBlocking():
        logBridgeSkip("not_enabled", "[bridge:repl] Skipping: bridge not enabled")
        return None

    # 2. Check OAuth
    if not getBridgeAccessToken():
        logBridgeSkip("no_oauth", "[bridge:repl] Skipping: no OAuth tokens")
        if on_state_change:
            on_state_change("failed", "/login")
        return None

    # 3. Check organization policy
    try:
        from ..services.policy_limits import wait_for_policy_limits_to_load, is_policy_allowed
        await wait_for_policy_limits_to_load()
        if not is_policy_allowed("allow_remote_control"):
            logBridgeSkip("policy_denied", "[bridge:repl] Skipping: allow_remote_control policy not allowed")
            if on_state_change:
                on_state_change("failed", "disabled by your organization's policy")
            return None
    except Exception:
        pass

    # Token expiry checks (when not using override token)
    if not getBridgeTokenOverride():
        try:
            from ..utils.auth import check_and_refresh_oauth_token_if_needed, get_vivian_ai_oauth_tokens
            from ..utils.config import get_global_config, save_global_config
            import time

            cfg = get_global_config()
            tokens = get_vivian_ai_oauth_tokens()
            if (
                cfg.get("bridgeOauthDeadExpiresAt") is not None
                and (cfg.get("bridgeOauthDeadFailCount") or 0) >= 3
                and tokens
                and tokens.get("expiresAt") == cfg.get("bridgeOauthDeadExpiresAt")
            ):
                log_for_debugging("[bridge:repl] Skipping: cross-process backoff")
                return None

            await check_and_refresh_oauth_token_if_needed()
            tokens = get_vivian_ai_oauth_tokens()
            if tokens and tokens.get("expiresAt") is not None and tokens["expiresAt"] <= int(time.time() * 1000):
                logBridgeSkip("oauth_expired_unrefreshable", "[bridge:repl] Skipping: OAuth token expired")
                if on_state_change:
                    on_state_change("failed", "/login")
                dead_expires_at = tokens["expiresAt"]
                def _update_cfg(c):
                    return {**c, "bridgeOauthDeadExpiresAt": dead_expires_at,
                            "bridgeOauthDeadFailCount": (c.get("bridgeOauthDeadFailCount") or 0) + 1
                            if c.get("bridgeOauthDeadExpiresAt") == dead_expires_at else 1}
                save_global_config(_update_cfg)
                return None
        except Exception:
            pass

    # 4. Compute baseUrl
    base_url = getBridgeBaseUrl()

    # 5. Derive session title
    try:
        from ..utils.words import generate_short_word_slug
        title = f"remote-control-{generate_short_word_slug()}"
    except Exception:
        import uuid as _uuid
        title = f"remote-control-{str(_uuid.uuid4())[:8]}"

    has_title = False
    has_explicit_title = False

    if initial_name:
        title = initial_name
        has_title = True
        has_explicit_title = True
    else:
        try:
            from ..bootstrap.state import getSessionId
            from ..utils.session_storage import get_current_session_title
            session_id = getSessionId()
            custom_title = get_current_session_title(session_id) if session_id else None
            if custom_title:
                title = custom_title
                has_title = True
                has_explicit_title = True
        except Exception:
            pass

        if not has_title and initial_messages:
            for msg in reversed(initial_messages):
                if (msg.get("type") != "user" or msg.get("isMeta") or msg.get("toolUseResult")
                        or msg.get("isCompactSummary") or (msg.get("origin") and msg["origin"].get("kind") != "human")):
                    continue
                content = msg.get("message", {}).get("content", "")
                raw_content = content if isinstance(content, str) else next(
                    (b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"), ""
                )
                derived = _derive_title(raw_content)
                if derived:
                    title = derived
                    has_title = True
                    break

    # onUserMessage closure
    user_message_count = 0
    last_bridge_session_id: Optional[str] = None
    gen_seq = 0

    async def _patch(derived: str, bridge_session_id: str, at_count: int) -> None:
        nonlocal has_title, title
        has_title = True
        title = derived
        log_for_debugging(f"[bridge:repl] derived title from message {at_count}: {derived}")
        try:
            await updateBridgeSessionTitle(bridge_session_id, derived, base_url=base_url, get_access_token=getBridgeAccessToken)
        except Exception:
            pass

    def on_user_message(text: str, bridge_session_id: str) -> bool:
        nonlocal user_message_count, last_bridge_session_id, has_title, title, gen_seq
        try:
            from ..bootstrap.state import getSessionId
            from ..utils.session_storage import get_current_session_title
            if has_explicit_title or get_current_session_title(getSessionId()):
                return True
        except Exception:
            if has_explicit_title:
                return True

        if last_bridge_session_id is not None and last_bridge_session_id != bridge_session_id:
            user_message_count = 0
        last_bridge_session_id = bridge_session_id
        user_message_count += 1

        import asyncio

        if user_message_count == 1 and not has_title:
            placeholder = _derive_title(text)
            if placeholder:
                asyncio.ensure_future(_patch(placeholder, bridge_session_id, user_message_count))
        elif user_message_count == 3:
            try:
                from ..utils.session_title import generate_session_title
                msgs = get_messages() if get_messages else None
                input_text = text
                if msgs:
                    try:
                        from ..utils.messages import extract_conversation_text, get_messages_after_compact_boundary
                        input_text = extract_conversation_text(get_messages_after_compact_boundary(msgs))
                    except Exception:
                        pass
                seq = gen_seq + 1
                gen_seq = seq
                async def _gen_patch():
                    try:
                        generated = await generate_session_title(input_text)
                        if generated and gen_seq == seq:
                            await _patch(generated, bridge_session_id, user_message_count)
                    except Exception:
                        pass
                asyncio.ensure_future(_gen_patch())
            except Exception:
                pass

        return user_message_count >= 3

    # Fetch orgUUID
    try:
        from ..services.oauth.client import get_organization_uuid
        org_uuid = await get_organization_uuid()
        if not org_uuid:
            logBridgeSkip("no_org_uuid", "[bridge:repl] Skipping: no org UUID")
            if on_state_change:
                on_state_change("failed", "/login")
            return None
    except Exception as e:
        log_for_debugging(f"[bridge:repl] Could not get org UUID: {e}")
        org_uuid = None

    # GrowthBook gate: env-less bridge
    if isEnvLessBridgeEnabled() and not perpetual:
        version_error = await checkEnvLessBridgeMinVersion()
        if version_error:
            logBridgeSkip("version_too_old", f"[bridge:repl] Skipping: {version_error}", True)
            if on_state_change:
                on_state_change("failed", "run `vivian update` to upgrade")
            return None
        log_for_debugging("[bridge:repl] Using env-less bridge path (tengu_bridge_repl_v2)")
        try:
            from .remoteBridgeCore import initEnvLessBridgeCore
            return await initEnvLessBridgeCore(
                base_url=base_url,
                org_uuid=org_uuid,
                title=title,
                get_access_token=getBridgeAccessToken,
                on_inbound_message=on_inbound_message,
                on_user_message=on_user_message,
                on_permission_response=on_permission_response,
                on_interrupt=on_interrupt,
                on_set_model=on_set_model,
                on_set_max_thinking_tokens=on_set_max_thinking_tokens,
                on_set_permission_mode=on_set_permission_mode,
                on_state_change=on_state_change,
                initial_messages=initial_messages,
                outbound_only=outbound_only,
                tags=tags,
            )
        except Exception as e:
            log_for_debugging(f"[bridge:repl] initEnvLessBridgeCore failed: {e}")
            return None

    # v1 path: env-based
    version_error = checkBridgeMinVersion()
    if version_error:
        logBridgeSkip("version_too_old", f"[bridge:repl] Skipping: {version_error}")
        if on_state_change:
            on_state_change("failed", "run `vivian update` to upgrade")
        return None

    try:
        from ..utils.git import get_branch, get_remote_url
        branch = await get_branch()
        git_repo_url = await get_remote_url()
    except Exception:
        branch = ""
        git_repo_url = None

    import os
    session_ingress_url = (
        os.environ.get("vivian_BRIDGE_SESSION_INGRESS_URL")
        if os.environ.get("USER_TYPE") == "ant" and os.environ.get("vivian_BRIDGE_SESSION_INGRESS_URL")
        else base_url
    )

    worker_type = "vivian_code"

    try:
        from ..bootstrap.state import getOriginalCwd
        cwd = getOriginalCwd()
    except Exception:
        cwd = os.getcwd()

    try:
        from ..utils.messages.mappers import to_sdk_messages
        from ..utils.auth import handle_o_auth_401_error
        from .replBridge import initBridgeCore
        from ..utils.session_storage import get_current_session_title
        from ..bootstrap.state import getSessionId

        def _create_session(**kwargs: Any):
            return createBridgeSession(
                environment_id=kwargs["environment_id"],
                events=[],
                git_repo_url=git_repo_url,
                branch=branch,
                base_url=base_url,
                get_access_token=getBridgeAccessToken,
                title=kwargs.get("title"),
            )

        async def _archive_session(session_id: str) -> None:
            try:
                await archiveBridgeSession(session_id, base_url=base_url, get_access_token=getBridgeAccessToken, timeout_ms=1500)
            except Exception as err:
                log_for_debugging(f"[bridge:repl] archiveBridgeSession threw: {err}", level="error")

        def _get_current_title() -> str:
            try:
                return get_current_session_title(getSessionId()) or title
            except Exception:
                return title

        return await initBridgeCore(
            directory=cwd,
            machine_name=socket.gethostname(),
            branch=branch,
            git_repo_url=git_repo_url,
            title=title,
            base_url=base_url,
            session_ingress_url=session_ingress_url,
            worker_type=worker_type,
            get_access_token=getBridgeAccessToken,
            create_session=_create_session,
            archive_session=_archive_session,
            get_current_title=_get_current_title,
            on_user_message=on_user_message,
            to_sdk_messages=to_sdk_messages,
            on_auth_401=handle_o_auth_401_error,
            get_poll_interval_config=getPollIntervalConfig,
            initial_messages=initial_messages,
            previously_flushed_uuids=previously_flushed_uuids,
            on_inbound_message=on_inbound_message,
            on_permission_response=on_permission_response,
            on_interrupt=on_interrupt,
            on_set_model=on_set_model,
            on_set_max_thinking_tokens=on_set_max_thinking_tokens,
            on_set_permission_mode=on_set_permission_mode,
            on_state_change=on_state_change,
            perpetual=perpetual,
        )
    except Exception as e:
        log_for_debugging(f"[bridge:repl] initBridgeCore failed: {e}")
        return None
