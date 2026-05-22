"""Port of src/utils/imageStore.ts."""
from __future__ import annotations

import asyncio
import base64
from collections import OrderedDict
from pathlib import Path
from typing import Optional

IMAGE_STORE_DIR = "image-cache"
MAX_STORED_IMAGE_PATHS = 200

storedImagePaths: "OrderedDict[int, str]" = OrderedDict()


def getImageStoreDir():
    """Get the image store directory for the current session."""
    from ..bootstrap.state import getSessionId
    from .envUtils import get_vivian_config_home_dir

    return str(Path(get_vivian_config_home_dir()) / IMAGE_STORE_DIR / getSessionId())


async def ensureImageStoreDir():
    """Ensure the image store directory exists."""
    image_dir = Path(getImageStoreDir())
    await asyncio.to_thread(image_dir.mkdir, parents=True, exist_ok=True)


def getImagePath(imageId, mediaType):
    """Get the file path for an image by ID."""
    extension = str(mediaType or "image/png").split("/")[-1] or "png"
    return str(Path(getImageStoreDir()) / f"{imageId}.{extension}")


def cacheImagePath(content):
    """Cache the image path immediately (fast, no file I/O)."""
    if not isinstance(content, dict) or content.get("type") != "image":
        return None
    image_path = getImagePath(content.get("id"), content.get("mediaType") or "image/png")
    evictOldestIfAtCap()
    storedImagePaths[int(content.get("id"))] = image_path
    return image_path


async def storeImage(content):
    """Store an image from pastedContents to disk."""
    if not isinstance(content, dict) or content.get("type") != "image":
        return None

    try:
        from .debug import logForDebugging

        await ensureImageStoreDir()
        image_path = Path(getImagePath(content.get("id"), content.get("mediaType") or "image/png"))
        raw_content = content.get("content") or ""
        data = base64.b64decode(raw_content)
        await asyncio.to_thread(image_path.write_bytes, data)
        evictOldestIfAtCap()
        storedImagePaths[int(content.get("id"))] = str(image_path)
        logForDebugging(f"Stored image {content.get('id')} to {image_path}")
        return str(image_path)
    except Exception as error:
        try:
            from .debug import logForDebugging

            logForDebugging(f"Failed to store image: {error}")
        except Exception:
            pass
        return None


async def storeImages(pastedContents):
    """Store all images from pastedContents to disk."""
    path_map: dict[int, str] = {}
    if not isinstance(pastedContents, dict):
        return path_map

    for image_id, content in pastedContents.items():
        if isinstance(content, dict) and content.get("type") == "image":
            path = await storeImage(content)
            if path:
                path_map[int(image_id)] = path
    return path_map


def getStoredImagePath(imageId):
    """Get the file path for a stored image by ID."""
    try:
        return storedImagePaths.get(int(imageId))
    except Exception:
        return None


def clearStoredImagePaths():
    """Clear the in-memory cache of stored image paths."""
    storedImagePaths.clear()


def evictOldestIfAtCap():
    while len(storedImagePaths) >= MAX_STORED_IMAGE_PATHS:
        storedImagePaths.popitem(last=False)


async def cleanupOldImageCaches():
    """Clean up old image cache directories from previous sessions."""
    from ..bootstrap.state import getSessionId
    from .envUtils import get_vivian_config_home_dir

    base_dir = Path(get_vivian_config_home_dir()) / IMAGE_STORE_DIR
    current_session_id = getSessionId()

    try:
        if not await asyncio.to_thread(base_dir.exists):
            return
        for entry in await asyncio.to_thread(lambda: list(base_dir.iterdir())):
            if not entry.is_dir() or entry.name == current_session_id:
                continue
            try:
                for child in entry.rglob("*"):
                    if child.is_file() or child.is_symlink():
                        child.unlink(missing_ok=True)
                for child_dir in sorted((p for p in entry.rglob("*") if p.is_dir()), reverse=True):
                    child_dir.rmdir()
                entry.rmdir()
            except Exception:
                continue
        try:
            if not any(base_dir.iterdir()):
                base_dir.rmdir()
        except Exception:
            pass
    except Exception:
        return


get_image_store_dir = getImageStoreDir
ensure_image_store_dir = ensureImageStoreDir
get_image_path = getImagePath
cache_image_path = cacheImagePath
store_image = storeImage
store_images = storeImages
get_stored_image_path = getStoredImagePath
clear_stored_image_paths = clearStoredImagePaths
cleanup_old_image_caches = cleanupOldImageCaches

