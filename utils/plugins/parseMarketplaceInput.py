"""
Port of src/utils/plugins/parseMarketplaceInput.ts

Parses a marketplace input string into a MarketplaceSource.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse


async def parseMarketplaceInput(input_str: str) -> Optional[Dict[str, Any]]:
    """Parses a marketplace input string and returns the appropriate marketplace source."""
    trimmed = input_str.strip()

    # Git SSH URLs
    ssh_match = re.match(r"^([a-zA-Z0-9._-]+@[^:]+:.+?(?:\.git)?)(?:#(.+))?$", trimmed)
    if ssh_match:
        url = ssh_match.group(1)
        ref = ssh_match.group(2)
        return {"source": "git", "url": url, **({"ref": ref} if ref else {})}

    # HTTP/HTTPS URLs
    if trimmed.startswith("http://") or trimmed.startswith("https://"):
        fragment_match = re.match(r"^([^#]+)(?:#(.+))?$", trimmed)
        url_without_fragment = fragment_match.group(1) if fragment_match else trimmed
        ref = fragment_match.group(2) if fragment_match else None

        if url_without_fragment.endswith(".git") or "/_git/" in url_without_fragment:
            return {"source": "git", "url": url_without_fragment, **({"ref": ref} if ref else {})}

        try:
            parsed = urlparse(url_without_fragment)
        except Exception:
            return {"source": "url", "url": url_without_fragment}

        if parsed.hostname in ("github.com", "www.github.com"):
            match = re.match(r"^/([^/]+/[^/]+?)(?:/|\.git|$)", parsed.path)
            if match:
                git_url = url_without_fragment if url_without_fragment.endswith(".git") else f"{url_without_fragment}.git"
                return {"source": "git", "url": git_url, **({"ref": ref} if ref else {})}

        return {"source": "url", "url": url_without_fragment}

    # Local paths
    is_windows = os.name == "nt"
    is_windows_path = is_windows and (
        trimmed.startswith(".\\") or trimmed.startswith("..\\") or re.match(r"^[a-zA-Z]:[/\\]", trimmed)
    )
    if trimmed.startswith("./") or trimmed.startswith("../") or trimmed.startswith("/") or trimmed.startswith("~") or is_windows_path:
        resolved = os.path.expanduser(trimmed) if trimmed.startswith("~") else trimmed
        resolved = os.path.abspath(resolved)

        if not os.path.exists(resolved):
            return {"error": f"Path does not exist: {resolved}"}

        if os.path.isfile(resolved):
            if resolved.endswith(".json"):
                return {"source": "file", "path": resolved}
            return {"error": f"File path must point to a .json file, but got: {resolved}"}
        elif os.path.isdir(resolved):
            return {"source": "directory", "path": resolved}
        return {"error": f"Path is neither a file nor a directory: {resolved}"}

    # GitHub shorthand (owner/repo)
    if "/" in trimmed and not trimmed.startswith("@") and ":" not in trimmed:
        fragment_match = re.match(r"^([^#@]+)(?:[#@](.+))?$", trimmed)
        repo = fragment_match.group(1) if fragment_match else trimmed
        ref = fragment_match.group(2) if fragment_match else None
        return {"source": "github", "repo": repo, **({"ref": ref} if ref else {})}

    return None

