"""
    pass of src/utils/browser
"""
from __future__ import annotations

import asyncio
import os
import os.path
import platform
import subprocess
import webbrowser
from urllib.parse import urlparse
from typing import Any, Callable, Dict, List, Literal, Optional, Set, Tuple, TYPE_CHECKING, Union


def validateUrl(url):
    parsed = urlparse(str(url))
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL format: {url}")
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(
            f"Invalid URL protocol: must use http:// or https://, got {parsed.scheme}:"
        )
    return None


async def openPath(path):
    """Open a file or folder path using the system's default handler."""
    if not path:
        return False

    def _open() -> bool:
        try:
            system = platform.system()
            if system == "Windows":
                result = subprocess.run(["explorer", path], capture_output=True)
                return result.returncode == 0
            command = "open" if system == "Darwin" else "xdg-open"
            result = subprocess.run([command, path], capture_output=True)
            return result.returncode == 0
        except Exception:
            return False

    return await asyncio.to_thread(_open)


async def openBrowser(url):
    try:
        validateUrl(url)

        def _open() -> bool:
            browser_env = os.environ.get("BROWSER")
            system = platform.system()
            if system == "Windows":
                if browser_env:
                    result = subprocess.run([browser_env, url], capture_output=True)
                    return result.returncode == 0
                result = subprocess.run(["rundll32", "url.dll,FileProtocolHandler", url], capture_output=True)
                return result.returncode == 0

            command = browser_env or ("open" if system == "Darwin" else "xdg-open")
            result = subprocess.run([command, url], capture_output=True)
            return result.returncode == 0

        return await asyncio.to_thread(_open)
    except Exception:
        return False


validate_url = validateUrl


async def open_browser(url):
    return await openBrowser(url)


async def open_path(path):
    return await openPath(path)
