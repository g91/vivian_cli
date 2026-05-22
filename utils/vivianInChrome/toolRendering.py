"""Port of src/utils/vivianInChrome/toolRendering.tsx."""
from __future__ import annotations

from typing import Any

ChromeToolName = str

CHROME_EXTENSION_FOCUS_TAB_URL_BASE = "https://api-vivian.d0a.net/chrome/tab/"

_RESULT_SUMMARY: dict[str, str] = {
    "navigate": "Navigated",
    "javascript_tool": "Executed",
    "read_page": "Read",
    "find": "Found",
    "form_input": "Filled",
    "computer": "Action performed",
    "resize_window": "Resized",
    "gif_creator": "Recorded",
    "upload_image": "Uploaded",
    "get_page_text": "Extracted",
    "tabs_context_mcp": "Listed",
    "tabs_create_mcp": "Created",
    "update_plan": "Updated",
    "read_console_messages": "Read",
    "read_network_requests": "Read",
    "shortcuts_list": "Listed",
    "shortcuts_execute": "Executed",
}


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: max(0, width - 1)] + "\u2026"


def renderChromeToolUseMessage(input: dict[str, Any], toolName: ChromeToolName, verbose: bool) -> str:
    if toolName == "navigate":
        url = input.get("url", "")
        return _truncate(str(url), 60)
    if toolName == "javascript_tool":
        code = input.get("code", "")
        return _truncate(str(code), 40)
    if toolName == "find":
        text = input.get("text", "")
        return _truncate(str(text), 40)
    if toolName == "form_input":
        return str(input.get("selector", ""))
    if toolName == "resize_window":
        return f"{input.get('width')}x{input.get('height')}"
    if toolName == "upload_image":
        return str(input.get("path", ""))
    if toolName == "read_console_messages":
        pattern = input.get("pattern")
        return f"pattern: {pattern}" if pattern else ""
    if toolName == "read_network_requests":
        pattern = input.get("pattern")
        return f"pattern: {pattern}" if pattern else ""
    if toolName == "shortcuts_execute":
        return str(input.get("shortcut_id", ""))
    return ""


def renderChromeViewTabLink(input: dict[str, Any] | None) -> str | None:
    if not isinstance(input, dict):
        return None
    tab_id = input.get("tabId")
    if not isinstance(tab_id, (int, float)):
        return None
    return f"{CHROME_EXTENSION_FOCUS_TAB_URL_BASE}{int(tab_id)}"


def renderChromeToolResultMessage(
    output: str | dict[str, Any], toolName: ChromeToolName, verbose: bool
) -> str | None:
    if verbose:
        return None
    if isinstance(output, dict) and output.get("is_error"):
        return None
    return _RESULT_SUMMARY.get(toolName)


def getvivianInChromeMCPToolOverrides(toolName: str) -> dict[str, Any]:
    def userFacingName(input: dict[str, Any] | None = None) -> str:
        return f"Chrome[{toolName}]"

    return {
        "userFacingName": userFacingName,
        "renderToolUseMessage": lambda input, options: renderChromeToolUseMessage(
            input, toolName, options.get("verbose", False) if isinstance(options, dict) else False
        ),
        "renderToolUseTag": lambda input: renderChromeViewTabLink(input),
        "renderToolResultMessage": lambda output, progressMessages, options: renderChromeToolResultMessage(
            output, toolName, options.get("verbose", False) if isinstance(options, dict) else False
        ),
    }


def isMCPToolResult(output: str | dict[str, Any]) -> bool:
    return isinstance(output, dict)


render_chrome_tool_use_message = renderChromeToolUseMessage
render_chrome_view_tab_link = renderChromeViewTabLink
render_chrome_tool_result_message = renderChromeToolResultMessage
get_vivian_in_chrome_mcp_tool_overrides = getvivianInChromeMCPToolOverrides
is_mcp_tool_result = isMCPToolResult

