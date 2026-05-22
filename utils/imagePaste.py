"""Port of src/utils/imagePaste.ts."""
from __future__ import annotations

import os
import re
import asyncio
import base64
import shutil
from pathlib import Path
from typing import Any, Dict, Optional


SupportedPlatform = str
ImageWithDimensions = Dict[str, Any]


PASTE_THRESHOLD: Any = 800  # type: ignore
# Regex pattern to match supported image file extensions. Kept in sync with
IMAGE_EXTENSION_REGEX = re.compile(r"\.(png|jpe?g|gif|webp)$", re.IGNORECASE)


def _tmp_image_path() -> str:
    base_tmp_dir = os.environ.get("vivian_CODE_TMPDIR") or os.environ.get("TMPDIR") or "/tmp"
    return str(Path(base_tmp_dir) / "vivian_cli_latest_screenshot.png")


def getClipboardCommands():
    platform_name = os.sys.platform
    screenshot_path = _tmp_image_path()

    commands = {
        "darwin": {
            "checkImage": ["osascript", "-e", "the clipboard as «class PNGf»"],
            "saveImage": [
                "osascript",
                "-e",
                "set png_data to (the clipboard as «class PNGf»)",
                "-e",
                f'set fp to open for access POSIX file "{screenshot_path}" with write permission',
                "-e",
                "write png_data to fp",
                "-e",
                "close access fp",
            ],
            "getPath": ["osascript", "-e", "get POSIX path of (the clipboard as «class furl»)"],
        },
        "linux": {
            "checkImage": ["sh", "-lc", "xclip -selection clipboard -t TARGETS -o 2>/dev/null | grep -E 'image/(png|jpeg|jpg|gif|webp|bmp)' || wl-paste -l 2>/dev/null | grep -E 'image/(png|jpeg|jpg|gif|webp|bmp)'"] ,
            "saveImage": ["sh", "-lc", f"xclip -selection clipboard -t image/png -o > '{screenshot_path}' 2>/dev/null || wl-paste --type image/png > '{screenshot_path}' 2>/dev/null || xclip -selection clipboard -t image/bmp -o > '{screenshot_path}' 2>/dev/null || wl-paste --type image/bmp > '{screenshot_path}'"],
            "getPath": ["sh", "-lc", "xclip -selection clipboard -t text/plain -o 2>/dev/null || wl-paste 2>/dev/null"],
        },
        "win32": {
            "checkImage": ["powershell", "-NoProfile", "-Command", "(Get-Clipboard -Format Image) -ne $null"],
            "saveImage": ["powershell", "-NoProfile", "-Command", f"$img = Get-Clipboard -Format Image; if ($img) {{$img.Save('{screenshot_path}', [System.Drawing.Imaging.ImageFormat]::Png)}}"],
            "getPath": ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
        },
    }
    return {"commands": commands.get(platform_name, commands["linux"]), "screenshotPath": screenshot_path}


async def hasImageInClipboard():
    """Check if clipboard contains an image without retrieving it."""
    from .execFileNoThrow import exec_file_no_throw

    data = getClipboardCommands()
    cmd = data["commands"]["checkImage"]
    result = await exec_file_no_throw(cmd[0], cmd[1:])
    return result.get("code") == 0


async def getImageFromClipboard():
    from .execFileNoThrow import exec_file_no_throw
    from .imageResizer import detectImageFormatFromBase64, maybeResizeAndDownsampleImageBuffer

    data = getClipboardCommands()
    commands = data["commands"]
    screenshot_path = Path(data["screenshotPath"])

    check = await exec_file_no_throw(commands["checkImage"][0], commands["checkImage"][1:])
    if check.get("code") != 0:
        return None

    saved = await exec_file_no_throw(commands["saveImage"][0], commands["saveImage"][1:])
    if saved.get("code") != 0 or not screenshot_path.exists():
        return None

    try:
        image_buffer = await asyncio.to_thread(screenshot_path.read_bytes)
        resized = await maybeResizeAndDownsampleImageBuffer(image_buffer, len(image_buffer), "png")
        base64_image = base64.b64encode(resized["buffer"]).decode("ascii")
        return {
            "base64": base64_image,
            "mediaType": detectImageFormatFromBase64(base64_image),
            "dimensions": resized.get("dimensions"),
        }
    except Exception:
        return None
    finally:
        try:
            screenshot_path.unlink(missing_ok=True)
        except Exception:
            pass


async def getImagePathFromClipboard():
    from .execFileNoThrow import exec_file_no_throw

    data = getClipboardCommands()
    cmd = data["commands"]["getPath"]
    result = await exec_file_no_throw(cmd[0], cmd[1:])
    if result.get("code") != 0:
        return None
    output = (result.get("stdout") or "").strip()
    return output or None


def removeOuterQuotes(text):
    """Remove outer single or double quotes from a string"""
    if not isinstance(text, str):
        return text
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return text[1:-1]
    return text


def stripBackslashEscapes(path):
    """Remove shell escape backslashes from a path (for macOS/Linux/WSL)"""
    if os.sys.platform == "win32" or not isinstance(path, str):
        return path
    placeholder = "__DOUBLE_BACKSLASH__"
    with_placeholder = path.replace("\\\\", placeholder)
    without_escapes = re.sub(r"\\(.)", r"\1", with_placeholder)
    return without_escapes.replace(placeholder, "\\")


def isImageFilePath(text):
    """Check if a given text represents an image file path"""
    if not isinstance(text, str):
        return False
    cleaned = removeOuterQuotes(text.strip())
    unescaped = stripBackslashEscapes(cleaned)
    return bool(IMAGE_EXTENSION_REGEX.search(unescaped))


def asImageFilePath(text):
    """Clean and normalize a text string that might be an image file path"""
    if not isinstance(text, str):
        return None
    cleaned = removeOuterQuotes(text.strip())
    unescaped = stripBackslashEscapes(cleaned)
    return unescaped if IMAGE_EXTENSION_REGEX.search(unescaped) else None


async def tryReadImageFromPath(text):
    """Try to find and read an image file, falling back to clipboard search"""
    from .imageResizer import detectImageFormatFromBase64, maybeResizeAndDownsampleImageBuffer

    image_path = asImageFilePath(text)
    if not image_path:
        return None

    target_path: Optional[Path] = None
    candidate = Path(image_path).expanduser()
    if candidate.is_absolute() and candidate.is_file():
        target_path = candidate
    else:
        clipboard_path = await getImagePathFromClipboard()
        if clipboard_path:
            clipboard_candidate = Path(clipboard_path).expanduser()
            if clipboard_candidate.is_file() and clipboard_candidate.name == candidate.name:
                target_path = clipboard_candidate

    if target_path is None:
        return None

    try:
        image_buffer = await asyncio.to_thread(target_path.read_bytes)
        if not image_buffer:
            return None
        ext = target_path.suffix.lstrip(".") or "png"
        resized = await maybeResizeAndDownsampleImageBuffer(image_buffer, len(image_buffer), ext)
        base64_image = base64.b64encode(resized["buffer"]).decode("ascii")
        return {
            "path": str(target_path),
            "base64": base64_image,
            "mediaType": detectImageFormatFromBase64(base64_image),
            "dimensions": resized.get("dimensions"),
        }
    except Exception:
        return None


get_clipboard_commands = getClipboardCommands
has_image_in_clipboard = hasImageInClipboard
get_image_from_clipboard = getImageFromClipboard
get_image_path_from_clipboard = getImagePathFromClipboard
remove_outer_quotes = removeOuterQuotes
strip_backslash_escapes = stripBackslashEscapes
is_image_file_path = isImageFilePath
as_image_file_path = asImageFilePath
try_read_image_from_path = tryReadImageFromPath

