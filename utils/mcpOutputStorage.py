"""
Port of src/utils/mcpOutputStorage.ts
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from ..services.analytics.index import logEvent
from .envUtils import get_vivian_config_home_dir
from .errors import to_error
from .format import format_bytes
from .log import logError


PersistBinaryResult = Any

_MIME_EXTENSIONS = {
    "application/pdf": "pdf",
    "application/json": "json",
    "text/csv": "csv",
    "text/plain": "txt",
    "text/html": "html",
    "text/markdown": "md",
    "application/zip": "zip",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/msword": "doc",
    "application/vnd.ms-excel": "xls",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/ogg": "ogg",
    "video/mp4": "mp4",
    "video/webm": "webm",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/svg+xml": "svg",
}


def _get_tool_results_dir() -> Path:
    try:
        from ..bootstrap.state import getSessionId, getSessionProjectDir

        session_id = getSessionId()
        project_dir = getSessionProjectDir()
        if project_dir:
            return Path(project_dir) / session_id / "tool-results"
        return Path(get_vivian_config_home_dir()) / "tool-results" / session_id
    except Exception:
        return Path(get_vivian_config_home_dir()) / "tool-results" / "unknown-session"


def getFormatDescription(type, schema=None):
    """Generates a format description string based on the MCP result type and schema."""
    if type == "toolResult":
        return "Plain text"
    if type == "structuredContent":
        return f"JSON with schema: {schema}" if schema is not None else "JSON"
    if type == "contentArray":
        return f"JSON array with schema: {schema}" if schema is not None else "JSON array"
    return "Unknown format"


def getLargeOutputInstructions(rawOutputPath, contentLength, formatDescription, maxReadLength=None):
    """Generates instruction text for vivian to read from a saved output file.

@param rawOutputPath - Path to the saved output file
@param contentLength - Length of the content in characters
@param formatDescription - Description of the content format
@param maxReadLength - Optional max chars for Read tool (for Bash output context)
@returns Instruction text to include in the tool result"""
    base_instructions = (
        f"Error: result ({contentLength:,} characters) exceeds maximum allowed tokens. Output has been saved to {rawOutputPath}.\n"
        f"Format: {formatDescription}\n"
        "Use offset and limit parameters to read specific portions of the file, search within it for specific content, and jq to make structured queries.\n"
        "REQUIREMENTS FOR SUMMARIZATION/ANALYSIS/REVIEW:\n"
        f"- You MUST read the content from the file at {rawOutputPath} in sequential chunks until 100% of the content has been read.\n"
    )
    truncation_warning = (
        f"- If you receive truncation warnings when reading the file (\"[N lines truncated]\"), reduce the chunk size until you have read 100% of the content without truncation ***DO NOT PROCEED UNTIL YOU HAVE DONE THIS***. Bash output is limited to {maxReadLength:,} chars.\n"
        if maxReadLength is not None
        else "- If you receive truncation warnings when reading the file, reduce the chunk size until you have read 100% of the content without truncation.\n"
    )
    completion_requirement = (
        "- Before producing ANY summary or analysis, you MUST explicitly describe what portion of the content you have read. ***If you did not read the entire content, you MUST explicitly state this.***\n"
    )
    return base_instructions + truncation_warning + completion_requirement


def extensionForMimeType(mimeType):
    """Map a mime type to a file extension. Conservative: known types get their
proper extension; unknown types get 'bin'. The extension matters because
the Read tool dispatches on it (PDFs, images, etc. need the right ext)."""
    if not mimeType:
        return "bin"
    mt = str(mimeType).split(";", 1)[0].strip().lower()
    return _MIME_EXTENSIONS.get(mt, "bin")


def isBinaryContentType(contentType):
    """Heuristic for whether a content-type header indicates binary content that
should be saved to disk rather than put into the model context.
Text-ish types (text/*, json, xml, form data) are treated as non-binary."""
    if not contentType:
        return False
    mt = str(contentType).split(";", 1)[0].strip().lower()
    if mt.startswith("text/"):
        return False
    if mt.endswith("+json") or mt == "application/json":
        return False
    if mt.endswith("+xml") or mt == "application/xml":
        return False
    if mt.startswith("application/javascript"):
        return False
    if mt == "application/x-www-form-urlencoded":
        return False
    return True


async def persistBinaryContent(bytes, mimeType, persistId):
    """Write raw binary bytes to the tool-results directory with a mime-derived
extension. Unlike persistToolResult (which stringifies), this writes the
bytes as-is so the resulting file can be opened with native tools (Read
for PDFs, pandas for xlsx, etc.)."""
    tool_results_dir = _get_tool_results_dir()
    await asyncio.to_thread(tool_results_dir.mkdir, parents=True, exist_ok=True)
    ext = extensionForMimeType(mimeType)
    filepath = tool_results_dir / f"{persistId}.{ext}"

    try:
        await asyncio.to_thread(filepath.write_bytes, bytes)
    except Exception as error:
        err = to_error(error)
        logError(err)
        return {"error": str(err)}

    logEvent(
        "tengu_binary_content_persisted",
        {
            "mimeType": mimeType or "unknown",
            "sizeBytes": len(bytes),
            "ext": ext,
        },
    )
    return {"filepath": str(filepath), "size": len(bytes), "ext": ext}


def getBinaryBlobSavedMessage(filepath, mimeType, size, sourceDescription):
    """Build a short message telling vivian where binary content was saved.
Just states the path — no prescriptive hint, since what the model can
actually do with the file depends on provider/tooling."""
    mt = mimeType or "unknown type"
    return f"{sourceDescription}Binary content ({mt}, {format_bytes(size)}) saved to {filepath}"


get_format_description = getFormatDescription
get_large_output_instructions = getLargeOutputInstructions
extension_for_mime_type = extensionForMimeType
is_binary_content_type = isBinaryContentType
persist_binary_content = persistBinaryContent
get_binary_blob_saved_message = getBinaryBlobSavedMessage

