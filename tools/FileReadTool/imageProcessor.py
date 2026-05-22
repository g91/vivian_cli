"""Image processor — mirrors src/tools/FileReadTool/imageProcessor.ts"""
from __future__ import annotations
import base64
import os
from typing import Dict, Optional

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico"}

IMAGE_MIMETYPES: Dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}

def isImageFile(filePath: str) -> bool:
    """Check if a file is an image based on its extension."""
    ext = os.path.splitext(filePath)[1].lower()
    return ext in IMAGE_EXTENSIONS

def getImageMimeType(filePath: str) -> str:
    """Get the MIME type for an image file."""
    ext = os.path.splitext(filePath)[1].lower()
    return IMAGE_MIMETYPES.get(ext, "application/octet-stream")

def encodeImageBase64(filePath: str) -> Optional[str]:
    """Read an image file and encode it as base64."""
    try:
        with open(filePath, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode("ascii")
    except (FileNotFoundError, PermissionError):
        return None

def buildImageToolResult(filePath: str) -> Optional[Dict[str, str]]:
    """Build a tool result for an image file."""
    b64 = encodeImageBase64(filePath)
    if b64 is None:
        return None
    mime = getImageMimeType(filePath)
    return {
        "type": "image",
        "mimeType": mime,
        "data": b64,
        "path": filePath,
    }
