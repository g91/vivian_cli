"""Port of src/utils/computerUse/wrapper.tsx."""
from __future__ import annotations

import asyncio
from typing import Any

from ...bootstrap.state import getSessionId
from ..debug import logForDebugging
from .computerUseLock import checkComputerUseLock, tryAcquireComputerUseLock
from .escHotkey import registerEscHotkey
from .gates import getChicagoCoordinateMode
from .hostAdapter import getComputerUseHostAdapter
from .toolRendering import getComputerUseMCPRenderingOverrides

CallOverride = Any
Binding = dict[str, Any]
ComputerUseMCPToolOverrides = Any

_binding: Binding | None = None
_current_tool_use_context: Any = None


def tuc() -> Any:
    return _current_tool_use_context


def formatLockHeld(holder: str) -> str:
    return f"Computer use is in use by another vivian session ({holder[:8]}\u2026). Wait for that session to finish or run /exit there."


def buildSessionContext() -> dict[str, Any]:
    return {
        "getAllowedApps": lambda: (tuc().getAppState().get("computerUseMcpState") or {}).get("allowedApps", []),
        "getGrantFlags": lambda: (tuc().getAppState().get("computerUseMcpState") or {}).get("grantFlags", {"clipboardRead": False, "clipboardWrite": False, "systemKeyCombos": False}),
        "getUserDeniedBundleIds": lambda: [],
        "getSelectedDisplayId": lambda: (tuc().getAppState().get("computerUseMcpState") or {}).get("selectedDisplayId"),
        "getDisplayPinnedByModel": lambda: (tuc().getAppState().get("computerUseMcpState") or {}).get("displayPinnedByModel", False),
        "getDisplayResolvedForApps": lambda: (tuc().getAppState().get("computerUseMcpState") or {}).get("displayResolvedForApps"),
        "getLastScreenshotDims": lambda: _get_last_screenshot_dims(),
        "onPermissionRequest": lambda req, _dialogSignal: runPermissionDialog(req),
        "onAllowedAppsChanged": lambda apps, flags: _on_allowed_apps_changed(apps, flags),
        "onAppsHidden": lambda ids: _on_apps_hidden(ids),
        "onResolvedDisplayUpdated": lambda id: _on_resolved_display_updated(id),
        "onDisplayPinned": lambda id: _on_display_pinned(id),
        "onDisplayResolvedForApps": lambda key: _on_display_resolved_for_apps(key),
        "onScreenshotCaptured": lambda dims: _on_screenshot_captured(dims),
        "checkCuLock": lambda: _check_cu_lock(),
        "acquireCuLock": lambda: _acquire_cu_lock(),
        "formatLockHeldMessage": formatLockHeld,
    }


def _get_last_screenshot_dims() -> dict[str, Any] | None:
    d = (tuc().getAppState().get("computerUseMcpState") or {}).get("lastScreenshotDims")
    if d:
        return {
            "width": d.get("width", 0),
            "height": d.get("height", 0),
            "displayWidth": d.get("displayWidth", 0),
            "displayHeight": d.get("displayHeight", 0),
            "displayId": d.get("displayId", 0),
            "originX": d.get("originX", 0),
            "originY": d.get("originY", 0),
        }
    return None


def _on_allowed_apps_changed(apps: list[dict[str, Any]], flags: dict[str, bool]) -> None:
    def _update(prev: dict[str, Any]) -> dict[str, Any]:
        cu = prev.get("computerUseMcpState") or {}
        prev_apps = cu.get("allowedApps")
        prev_flags = cu.get("grantFlags")
        same_apps = (
            prev_apps is not None
            and len(prev_apps) == len(apps)
            and all(
                (prev_apps[i] or {}).get("bundleId") == a.get("bundleId")
                for i, a in enumerate(apps)
            )
        )
        same_flags = (
            prev_flags is not None
            and prev_flags.get("clipboardRead") == flags.get("clipboardRead")
            and prev_flags.get("clipboardWrite") == flags.get("clipboardWrite")
            and prev_flags.get("systemKeyCombos") == flags.get("systemKeyCombos")
        )
        if same_apps and same_flags:
            return prev
        return {
            **prev,
            "computerUseMcpState": {
                **cu,
                "allowedApps": list(apps),
                "grantFlags": flags,
            },
        }

    tuc().setAppState(_update)


def _on_apps_hidden(ids: list[str]) -> None:
    if not ids:
        return

    def _update(prev: dict[str, Any]) -> dict[str, Any]:
        cu = prev.get("computerUseMcpState") or {}
        existing = cu.get("hiddenDuringTurn")
        if existing and all(id in existing for id in ids):
            return prev
        return {
            **prev,
            "computerUseMcpState": {
                **cu,
                "hiddenDuringTurn": set((existing or []) + list(ids)),
            },
        }

    tuc().setAppState(_update)


def _on_resolved_display_updated(id: int | None) -> None:
    def _update(prev: dict[str, Any]) -> dict[str, Any]:
        cu = prev.get("computerUseMcpState") or {}
        if (
            cu.get("selectedDisplayId") == id
            and not cu.get("displayPinnedByModel")
            and cu.get("displayResolvedForApps") is None
        ):
            return prev
        return {
            **prev,
            "computerUseMcpState": {
                **cu,
                "selectedDisplayId": id,
                "displayPinnedByModel": False,
                "displayResolvedForApps": None,
            },
        }

    tuc().setAppState(_update)


def _on_display_pinned(id: int | None) -> None:
    def _update(prev: dict[str, Any]) -> dict[str, Any]:
        cu = prev.get("computerUseMcpState") or {}
        pinned = id is not None
        next_resolved_for = cu.get("displayResolvedForApps") if pinned else None
        if (
            cu.get("selectedDisplayId") == id
            and cu.get("displayPinnedByModel") == pinned
            and cu.get("displayResolvedForApps") == next_resolved_for
        ):
            return prev
        return {
            **prev,
            "computerUseMcpState": {
                **cu,
                "selectedDisplayId": id,
                "displayPinnedByModel": pinned,
                "displayResolvedForApps": next_resolved_for,
            },
        }

    tuc().setAppState(_update)


def _on_display_resolved_for_apps(key: str | None) -> None:
    def _update(prev: dict[str, Any]) -> dict[str, Any]:
        cu = prev.get("computerUseMcpState") or {}
        if cu.get("displayResolvedForApps") == key:
            return prev
        return {
            **prev,
            "computerUseMcpState": {**cu, "displayResolvedForApps": key},
        }

    tuc().setAppState(_update)


def _on_screenshot_captured(dims: dict[str, Any]) -> None:
    def _update(prev: dict[str, Any]) -> dict[str, Any]:
        cu = prev.get("computerUseMcpState") or {}
        p = cu.get("lastScreenshotDims")
        if (
            p
            and p.get("width") == dims.get("width")
            and p.get("height") == dims.get("height")
            and p.get("displayWidth") == dims.get("displayWidth")
            and p.get("displayHeight") == dims.get("displayHeight")
            and p.get("displayId") == dims.get("displayId")
            and p.get("originX") == dims.get("originX")
            and p.get("originY") == dims.get("originY")
        ):
            return prev
        return {
            **prev,
            "computerUseMcpState": {**cu, "lastScreenshotDims": dims},
        }

    tuc().setAppState(_update)


async def _check_cu_lock() -> dict[str, Any]:
    c = await checkComputerUseLock()
    kind = c["kind"]
    if kind == "free":
        return {"holder": None, "isSelf": False}
    elif kind == "held_by_self":
        return {"holder": getSessionId(), "isSelf": True}
    elif kind == "blocked":
        return {"holder": c["by"], "isSelf": False}
    return {"holder": None, "isSelf": False}


async def _acquire_cu_lock() -> None:
    r = await tryAcquireComputerUseLock()
    if r["kind"] == "blocked":
        raise RuntimeError(formatLockHeld(r["by"]))
    if r.get("fresh"):
        esc_registered = registerEscHotkey(lambda: _on_esc_abort())
        tuc().sendOSNotification({
            "message": (
                "vivian is using your computer \u00b7 press Esc to stop"
                if esc_registered
                else "vivian is using your computer \u00b7 press Ctrl+C to stop"
            ),
            "notificationType": "computer_use_enter",
        })


def _on_esc_abort() -> None:
    logForDebugging("[cu-esc] user escape, aborting turn")
    ctx = tuc()
    if hasattr(ctx, "abortController") and ctx.abortController:
        ctx.abortController.abort()


def getOrBind() -> Binding:
    global _binding
    if _binding is not None:
        return _binding
    ctx = buildSessionContext()
    _binding = {
        "ctx": ctx,
        "dispatch": _bind_session_context(getComputerUseHostAdapter(), getChicagoCoordinateMode(), ctx),
    }
    return _binding


def _bind_session_context(adapter: dict[str, Any], coordinate_mode: str, ctx: dict[str, Any]) -> Any:
    """Stub for bindSessionContext from @ant/computer-use-mcp.
    In the real implementation, this would create a dispatcher that routes tool calls
    through the adapter's executor with the session context applied."""
    async def dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
        executor = adapter.get("executor", {})
        # Route to the appropriate executor method based on tool name
        method_map = {
            "screenshot": "screenshot",
            "left_click": "leftClick",
            "right_click": "rightClick",
            "middle_click": "middleClick",
            "double_click": "doubleClick",
            "triple_click": "tripleClick",
            "mouse_move": "mouseMove",
            "left_click_drag": "leftClickDrag",
            "type": "type",
            "key": "key",
            "hold_key": "holdKey",
            "scroll": "scroll",
            "zoom": "zoom",
            "wait": "wait",
            "open_application": "openApplication",
            "cursor_position": "cursorPosition",
            "left_mouse_down": "leftMouseDown",
            "left_mouse_up": "leftMouseUp",
            "read_clipboard": "readClipboard",
            "write_clipboard": "writeClipboard",
            "list_granted_applications": "listGrantedApplications",
            "request_access": "requestAccess",
            "computer_batch": "computerBatch",
        }
        method = method_map.get(name)
        if method and callable(executor.get(method)):
            result = await executor[method](**args)
            return {"content": [{"type": "text", "text": str(result)}]}
        return {"content": [{"type": "text", "text": f"Tool {name} executed"}]}

    return dispatch


def getComputerUseMCPToolOverrides(toolName: str) -> dict[str, Any]:
    async def call(args: dict[str, Any], context: Any) -> dict[str, Any]:
        global _current_tool_use_context
        _current_tool_use_context = context
        binding = getOrBind()
        dispatch = binding["dispatch"]
        result = await dispatch(toolName, args)

        telemetry = result.get("telemetry")
        if telemetry and telemetry.get("error_kind"):
            logForDebugging(f"[Computer Use MCP] {toolName} error_kind={telemetry['error_kind']}")

        content = result.get("content", [])
        if isinstance(content, list):
            data = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": item.get("mimeType", "image/jpeg"),
                        "data": item.get("data", ""),
                    },
                }
                if item.get("type") == "image"
                else {
                    "type": "text",
                    "text": item.get("text", "") if item.get("type") == "text" else "",
                }
                for item in content
            ]
        else:
            data = content

        return {"data": data}

    return {
        **getComputerUseMCPRenderingOverrides(toolName),
        "call": call,
    }


async def runPermissionDialog(req: dict[str, Any]) -> dict[str, Any]:
    context = tuc()
    set_tool_jsx = getattr(context, "setToolJSX", None)

    if not set_tool_jsx:
        return {"granted": [], "denied": [], "flags": {"clipboardRead": False, "clipboardWrite": False, "systemKeyCombos": False}}

    try:
        result = await _show_permission_dialog(req, context, set_tool_jsx)
        return result
    finally:
        set_tool_jsx(None)


async def _show_permission_dialog(
    req: dict[str, Any], context: Any, set_tool_jsx: Any
) -> dict[str, Any]:
    abort_controller = getattr(context, "abortController", None)
    signal = getattr(abort_controller, "signal", None) if abort_controller else None

    if signal and getattr(signal, "aborted", False):
        raise RuntimeError("Computer Use permission dialog aborted")

    future: asyncio.Future[dict[str, Any]] = asyncio.get_event_loop().create_future()

    def on_abort() -> None:
        if not future.done():
            future.set_exception(RuntimeError("Computer Use permission dialog aborted"))

    if signal and hasattr(signal, "addEventListener"):
        signal.addEventListener("abort", on_abort)

    def on_done(resp: dict[str, Any]) -> None:
        if signal and hasattr(signal, "removeEventListener"):
            signal.removeEventListener("abort", on_abort)
        if not future.done():
            future.set_result(resp)

    set_tool_jsx({
        "jsx": {"request": req, "onDone": on_done},
        "shouldHidePromptInput": True,
    })

    return await future


build_session_context = buildSessionContext
get_or_bind = getOrBind
get_computer_use_mcp_tool_overrides = getComputerUseMCPToolOverrides
run_permission_dialog = runPermissionDialog

