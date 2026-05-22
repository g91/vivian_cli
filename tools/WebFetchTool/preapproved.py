"""WebFetch preapproved domains — mirrors src/tools/WebFetchTool/preapproved.ts"""
from typing import List, Set

PREAPPROVED_DOMAINS: Set[str] = {
    "github.com",
    "docs.python.org",
    "pypi.org",
    "npmjs.com",
    "stackoverflow.com",
    "developer.mozilla.org",
    "nodejs.org",
    "typescriptlang.org",
}

def isPreapprovedDomain(url: str) -> bool:
    """Check if a URL's domain is pre-approved for fetching."""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain in PREAPPROVED_DOMAINS
    except Exception:
        return False
