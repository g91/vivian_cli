"""Port of src/utils/computerUse/toolRendering.tsx."""
from __future__ import annotations


RESULT_SUMMARY = {
    "screenshot": "Captured",
    "zoom": "Captured",
    "request_access": "Access updated",
    "left_click": "Clicked",
    "right_click": "Clicked",
    "middle_click": "Clicked",
    "double_click": "Clicked",
    "triple_click": "Clicked",
    "type": "Typed",
    "key": "Pressed",
    "hold_key": "Pressed",
    "scroll": "Scrolled",
    "left_click_drag": "Dragged",
    "open_application": "Opened",
}


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: max(0, width - 1)] + "…"


def fmtCoord(c):
    return f"({c[0]}, {c[1]})" if c else ""


def getComputerUseMCPRenderingOverrides(toolName):
    def userFacingName():
        return f"Computer Use[{toolName}]"

    def renderToolUseMessage(input, options=None):
        del options
        if toolName in {"screenshot", "left_mouse_down", "left_mouse_up", "cursor_position", "list_granted_applications", "read_clipboard"}:
            return ""
        if toolName in {"left_click", "right_click", "middle_click", "double_click", "triple_click", "mouse_move"}:
            return fmtCoord(input.get("coordinate"))
        if toolName == "left_click_drag":
            if input.get("start_coordinate"):
                return f"{fmtCoord(input.get('start_coordinate'))} -> {fmtCoord(input.get('coordinate'))}"
            return f"to {fmtCoord(input.get('coordinate'))}"
        if toolName in {"type", "write_clipboard"}:
            text = input.get("text")
            return f'"{_truncate(text, 40)}"' if isinstance(text, str) else ""
        if toolName in {"key", "hold_key"}:
            return input.get("text") if isinstance(input.get("text"), str) else ""
        if toolName == "scroll":
            parts = [input.get("direction"), f"x{input.get('amount')}" if input.get("amount") else None, f"at {fmtCoord(input.get('coordinate'))}" if input.get("coordinate") else None]
            return " ".join(str(part) for part in parts if part)
        if toolName == "zoom":
            region = input.get("region")
            return f"[{region[0]}, {region[1]}, {region[2]}, {region[3]}]" if isinstance(region, (list, tuple)) and len(region) == 4 else ""
        if toolName == "wait":
            return f"{input.get('duration')}s" if isinstance(input.get("duration"), (int, float)) else ""
        if toolName == "open_application":
            return str(input.get("bundle_id")) if isinstance(input.get("bundle_id"), str) else ""
        if toolName == "request_access":
            apps = input.get("apps")
            if not isinstance(apps, list):
                return ""
            names = [app.get("displayName", "") for app in apps if isinstance(app, dict) and isinstance(app.get("displayName"), str)]
            return ", ".join(name for name in names if name)
        if toolName == "computer_batch":
            actions = input.get("actions")
            return f"{len(actions)} actions" if isinstance(actions, list) else ""
        return ""

    def renderToolResultMessage(output, progressMessages=None, options=None):
        del progressMessages
        verbose = bool((options or {}).get("verbose"))
        if verbose or not isinstance(output, dict):
            return None
        return RESULT_SUMMARY.get(toolName)

    return {
        "userFacingName": userFacingName,
        "renderToolUseMessage": renderToolUseMessage,
        "renderToolResultMessage": renderToolResultMessage,
    }


fmt_coord = fmtCoord
get_computer_use_mcp_rendering_overrides = getComputerUseMCPRenderingOverrides

