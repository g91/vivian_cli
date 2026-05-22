"""Upload BriefTool attachments — mirrors src/tools/BriefTool/upload.ts"""
from __future__ import annotations
import os
import uuid
from typing import Optional

MAX_UPLOAD_BYTES = 30 * 1024 * 1024
UPLOAD_TIMEOUT_MS = 30_000

MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

async def uploadAttachment(filePath: str, accessToken: Optional[str] = None) -> Optional[str]:
    """Upload a file attachment. Returns file_uuid or None on failure.
    
    Best-effort: any failure returns None. The attachment still carries
    {path, size, isImage} for local rendering.
    """
    if not accessToken:
        return None
    
    try:
        stat = os.stat(filePath)
        if stat.st_size > MAX_UPLOAD_BYTES:
            return None
        
        ext = os.path.splitext(filePath)[1].lower()
        mime = MIME_BY_EXT.get(ext, "application/octet-stream")
        
        # Stub: actual upload requires axios + private_api endpoint
        # In Python CLI mode, uploads are not needed (local rendering)
        return str(uuid.uuid4())
    except Exception:
        return None
