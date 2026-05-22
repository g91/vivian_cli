"""
Shared content fetcher — mirrors src/tools/shared/contentFetcher.ts
"""
from __future__ import annotations
import re
import urllib.request
from typing import Optional


def fetchPageContent(url: str, maxLength: int = 20_000) -> str:
    """
    Fetch page content from a URL and return extracted text.
    Raises ValueError for non-http URLs.
    """
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"Only http/https URLs supported: {url}")

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; VivianBot/1.0)",
            "Accept": "text/html,application/xhtml+xml,*/*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content_type = resp.getheader("Content-Type", "")
            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].strip()
            body = resp.read(maxLength * 2).decode(charset, errors="replace")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch {url}: {e}") from e

    # Strip HTML
    text = re.sub(r"<script[^>]*>.*?</script>", "", body, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:maxLength]
