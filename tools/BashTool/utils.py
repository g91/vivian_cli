"""
BashTool utility functions — mirrors src/tools/BashTool/utils.ts
"""
from __future__ import annotations
import os
import re
from typing import Any, Dict, List, Optional, Tuple


def stripEmptyLines(text: str) -> str:
    """Remove leading and trailing empty lines."""
    lines = text.split("\n")
    # Strip leading empty lines
    while lines and not lines[0].strip():
        lines.pop(0)
    # Strip trailing empty lines
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def isImageOutput(stdout: str) -> bool:
    """Check if stdout contains base64-encoded image data."""
    return stdout.startswith("data:image/") or stdout.startswith("iVBORw0KGgo")


def buildImageToolResult(imageData: str, mimeType: str = "image/png") -> Dict[str, Any]:
    """Build a tool result containing image data."""
    if not imageData.startswith("data:"):
        imageData = f"data:{mimeType};base64,{imageData}"
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": mimeType, "data": imageData.split(",", 1)[1]},
    }


def stdErrAppendShellResetMessage(stderr: str, exitCode: int) -> str:
    """Append shell reset message to stderr if appropriate."""
    if exitCode != 0 and "command not found" in stderr.lower():
        return stderr + "\n[Shell environment may need to be reset]"
    return stderr


def resetCwdIfOutsideProject(cwd: str, projectRoot: str) -> str:
    """Reset working directory to project root if outside project."""
    if not cwd.startswith(projectRoot):
        return projectRoot
    return cwd


def resizeShellImageOutput(imageData: str, maxWidth: int = 1024) -> str:
    """Resize shell image output if too large (stub — requires PIL)."""
    return imageData
