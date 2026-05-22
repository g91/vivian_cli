"""Attachment validation — mirrors src/tools/BriefTool/attachments.ts"""
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico"}

@dataclass
class ResolvedAttachment:
    path: str
    size: int
    isImage: bool
    file_uuid: Optional[str] = None

async def validateAttachmentPaths(rawPaths: List[str], cwd: str = "") -> Dict[str, Any]:
    """Validate attachment paths exist and are regular files."""
    if not cwd:
        cwd = os.getcwd()
    for rawPath in rawPaths:
        fullPath = os.path.expanduser(rawPath)
        if not os.path.isabs(fullPath):
            fullPath = os.path.join(cwd, rawPath)
        try:
            if not os.path.isfile(fullPath):
                return {
                    "result": False,
                    "message": f'Attachment "{rawPath}" is not a regular file.',
                    "errorCode": 1,
                }
        except PermissionError:
            return {
                "result": False,
                "message": f'Permission denied reading "{rawPath}".',
                "errorCode": 1,
            }
        except FileNotFoundError:
            return {
                "result": False,
                "message": f'Attachment "{rawPath}" does not exist. Current working directory: {cwd}.',
                "errorCode": 1,
            }
    return {"result": True}

async def resolveAttachments(rawPaths: List[str], cwd: str = "") -> List[ResolvedAttachment]:
    """Resolve attachment paths to ResolvedAttachment objects."""
    if not cwd:
        cwd = os.getcwd()
    resolved: List[ResolvedAttachment] = []
    for rawPath in rawPaths:
        fullPath = os.path.expanduser(rawPath)
        if not os.path.isabs(fullPath):
            fullPath = os.path.join(cwd, rawPath)
        try:
            stat = os.stat(fullPath)
            ext = os.path.splitext(fullPath)[1].lower()
            resolved.append(ResolvedAttachment(
                path=fullPath,
                size=stat.st_size,
                isImage=ext in IMAGE_EXTENSIONS,
            ))
        except (FileNotFoundError, PermissionError):
            continue
    return resolved
