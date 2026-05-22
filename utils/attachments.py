"""Attachment helpers — mirrors src/utils/attachments.ts"""
from __future__ import annotations
from typing import Any

def is_image_content(block: Any) -> bool:
    if isinstance(block, dict):
        return block.get("type") == "image"
    if block is None:
        return False
    return True
