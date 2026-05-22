"""Port of src/utils/deepLink/parseDeepLink.ts."""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from ..sanitization import partially_sanitize_unicode


DEEP_LINK_PROTOCOL = "vivian-cli"
REPO_SLUG_PATTERN = re.compile(r"^[\w.-]+\/[\w.-]+$")
MAX_QUERY_LENGTH = 5000
MAX_CWD_LENGTH = 4096


@dataclass(slots=True)
class DeepLinkAction:
    query: str | None = None
    cwd: str | None = None
    repo: str | None = None


def containsControlChars(s: str) -> bool:
    return any(ord(ch) <= 0x1F or ord(ch) == 0x7F for ch in s)


def parseDeepLink(uri: str) -> DeepLinkAction:
    normalized = (
        uri
        if uri.startswith(f"{DEEP_LINK_PROTOCOL}://")
        else uri.replace(f"{DEEP_LINK_PROTOCOL}:", f"{DEEP_LINK_PROTOCOL}://", 1)
        if uri.startswith(f"{DEEP_LINK_PROTOCOL}:")
        else None
    )
    if not normalized:
        raise ValueError(f'Invalid deep link: expected {DEEP_LINK_PROTOCOL}:// scheme, got "{uri}"')

    try:
        parsed = urlparse(normalized)
    except Exception as exc:
        raise ValueError(f'Invalid deep link URL: "{uri}"') from exc

    if parsed.hostname != "open":
        raise ValueError(f'Unknown deep link action: "{parsed.hostname}"')

    params = parse_qs(parsed.query, keep_blank_values=True)
    cwd = params.get("cwd", [None])[0] or None
    repo = params.get("repo", [None])[0] or None
    raw_query = params.get("q", [None])[0]

    if cwd and not (cwd.startswith("/") or re.match(r"^[A-Za-z]:[/\\]", cwd)):
        raise ValueError(f'Invalid cwd in deep link: must be an absolute path, got "{cwd}"')
    if cwd and containsControlChars(cwd):
        raise ValueError("Deep link cwd contains disallowed control characters")
    if cwd and len(cwd) > MAX_CWD_LENGTH:
        raise ValueError(f"Deep link cwd exceeds {MAX_CWD_LENGTH} characters (got {len(cwd)})")
    if repo and not REPO_SLUG_PATTERN.match(repo):
        raise ValueError(f'Invalid repo in deep link: expected "owner/repo", got "{repo}"')

    query = None
    if raw_query and raw_query.strip():
        query = partially_sanitize_unicode(raw_query.strip())
        if containsControlChars(query):
            raise ValueError("Deep link query contains disallowed control characters")
        if len(query) > MAX_QUERY_LENGTH:
            raise ValueError(f"Deep link query exceeds {MAX_QUERY_LENGTH} characters (got {len(query)})")

    return DeepLinkAction(query=query, cwd=cwd, repo=repo)


def buildDeepLink(action: DeepLinkAction | dict) -> str:
    if isinstance(action, dict):
        action = DeepLinkAction(**action)
    query = {}
    if action.query:
        query["q"] = action.query
    if action.cwd:
        query["cwd"] = action.cwd
    if action.repo:
        query["repo"] = action.repo
    return urlunparse((DEEP_LINK_PROTOCOL, "open", "", "", urlencode(query), ""))


parse_deep_link = parseDeepLink
build_deep_link = buildDeepLink
contains_control_chars = containsControlChars

