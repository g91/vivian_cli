"""WebFetchTool utilities — mirrors src/tools/WebFetchTool/utils.ts"""
from typing import Optional
import re

def stripHtml(html: str) -> str:
    """Strip HTML tags from content, returning plain text."""
    # Remove script and style elements
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    # Decode common entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    return text.strip()

def extractTitle(html: str) -> Optional[str]:
    """Extract the title from HTML content."""
    match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def truncateContent(content: str, maxLength: int = 20000) -> str:
    """Truncate content to a maximum length."""
    if len(content) <= maxLength:
        return content
    return content[:maxLength] + "... [truncated]"
