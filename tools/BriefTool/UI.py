"""BriefTool UI — mirrors src/tools/BriefTool/UI.tsx"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...utils.file import getDisplayPath
from ...utils.formatBriefTimestamp import formatBriefTimestamp


def _format_file_size(num_bytes: Any) -> str:
    try:
        size = int(num_bytes or 0)
    except (TypeError, ValueError):
        size = 0

    units = ["B", "KB", "MB", "GB", "TB"]
    size_float = float(size)
    unit_index = 0
    while size_float >= 1024 and unit_index < len(units) - 1:
        size_float /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size_float)} {units[unit_index]}"
    return f"{size_float:.1f} {units[unit_index]}"


def _render_attachments(attachments: Any) -> str:
    if not isinstance(attachments, list) or not attachments:
        return ""

    lines: List[str] = []
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        path = getDisplayPath(str(attachment.get("path") or ""))
        kind = "[image]" if attachment.get("isImage") else "[file]"
        size = _format_file_size(attachment.get("size"))
        lines.append(f"> {kind} {path} ({size})")
    return "\n".join(lines)

def renderToolUseMessage() -> str:
    """Render the tool use message for BriefTool."""
    return ""

def renderToolResultMessage(
    output: Dict[str, Any],
    progressMessages: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Render the tool result message for BriefTool."""
    attachments = output.get("attachments", [])
    hasAttachments = len(attachments) > 0
    if not output.get("message") and not hasAttachments:
        return None

    message = output.get("message", "")
    attachment_text = _render_attachments(attachments)

    if options and options.get("isTranscriptMode"):
        if message and attachment_text:
            return f"\u23D0 {message}\n{attachment_text}"
        if message:
            return f"\u23D0 {message}"
        return attachment_text or None

    if options and options.get("isBriefOnly"):
        ts = formatBriefTimestamp(output.get("sentAt")) if output.get("sentAt") else ""
        header = "vivian"
        if ts:
            header += f" {ts}"
        body_parts = [part for part in (message, attachment_text) if part]
        if body_parts:
            return f"{header}\n" + "\n".join(body_parts)
        return header

    body_parts = [part for part in (message, attachment_text) if part]
    return "\n".join(body_parts) if body_parts else None

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for BriefTool."""
    return f"Error: {errorMessage}"
