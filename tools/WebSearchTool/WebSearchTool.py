"""WebSearchTool — mirrors src/tools/WebSearchTool/WebSearchTool.tsx"""
from __future__ import annotations
import asyncio
import re
import time
import urllib.parse
import urllib.request
from html import unescape
from typing import Any, Dict
from urllib.parse import urlparse

TOOL_NAME = "WebSearch"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["query"],
    "properties": {
        "query": {"type": "string", "description": "Search query"},
        "allowed_domains": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Only include search results from these domains",
        },
        "blocked_domains": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Never include search results from these domains",
        },
        "num_results": {"type": "integer", "description": "Number of results to return", "default": 5},
    },
}


_RESULT_RE = re.compile(
    r'<a[^>]*class="result__a"[^>]*href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_DDG_REDIRECT_RE = re.compile(r"[?&]uddg=([^&]+)")


async def description() -> str:
    return "Search the web for information."


async def prompt() -> str:
    return (
        "Use this tool to search the web for information. "
        "Provide a query and optionally allowed_domains or blocked_domains to filter results. "
        "Returns structured search hits and a summary of how many searches were performed."
    )


def getToolUseSummary(input_data: Dict[str, Any]) -> str:
    return input_data.get("query", "")


def _strip_tags(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", _TAG_RE.sub(" ", unescape(value))).strip()


def _extract_target_url(raw_url: str) -> str:
    match = _DDG_REDIRECT_RE.search(raw_url)
    if match:
        return urllib.parse.unquote(match.group(1))
    return urllib.parse.unquote(raw_url)


def _normalize_domains(values: Any) -> list[str]:
    normalized: list[str] = []
    if not isinstance(values, list):
        return normalized
    for value in values:
        text = str(value or "").strip().lower()
        if text:
            normalized.append(text.lstrip("."))
    return normalized


def _domain_allowed(url: str, allowed_domains: list[str], blocked_domains: list[str]) -> bool:
    hostname = (urlparse(url).hostname or "").lower().lstrip(".")
    if not hostname:
        return False
    if allowed_domains and not any(hostname == domain or hostname.endswith(f".{domain}") for domain in allowed_domains):
        return False
    if blocked_domains and any(hostname == domain or hostname.endswith(f".{domain}") for domain in blocked_domains):
        return False
    return True


def _parse_search_results(html: str, limit: int, allowed_domains: list[str], blocked_domains: list[str]) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in _RESULT_RE.finditer(html):
        target_url = _extract_target_url(match.group("url"))
        title = _strip_tags(match.group("title"))
        if not target_url or not title:
            continue
        if target_url in seen:
            continue
        if not _domain_allowed(target_url, allowed_domains, blocked_domains):
            continue
        seen.add(target_url)
        hits.append({"title": title, "url": target_url})
        if len(hits) >= limit:
            break
    return hits


async def _search_duckduckgo(query: str, limit: int, allowed_domains: list[str], blocked_domains: list[str]) -> list[dict[str, str]]:
    def _fetch() -> list[dict[str, str]]:
        params = urllib.parse.urlencode({"q": query})
        req = urllib.request.Request(
            f"https://html.duckduckgo.com/html/?{params}",
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; VivianBot/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
        return _parse_search_results(body, limit, allowed_domains, blocked_domains)

    return await asyncio.to_thread(_fetch)


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    del context
    query = str(input_data.get("query") or "").strip()
    allowed_domains = _normalize_domains(input_data.get("allowed_domains"))
    blocked_domains = _normalize_domains(input_data.get("blocked_domains"))
    limit = max(1, min(int(input_data.get("num_results", 5) or 5), 10))

    if len(query) < 2:
        return {"query": query, "results": ["Error: Missing query"], "durationSeconds": 0.0}
    if allowed_domains and blocked_domains:
        return {
            "query": query,
            "results": ["Error: Cannot specify both allowed_domains and blocked_domains in the same request"],
            "durationSeconds": 0.0,
        }

    start = time.perf_counter()
    try:
        hits = await _search_duckduckgo(query, limit, allowed_domains, blocked_domains)
        results: list[dict[str, Any] | str] = []
        if hits:
            results.append({"tool_use_id": "web-search-1", "content": hits})
        duration = time.perf_counter() - start
        return {"query": query, "results": results, "durationSeconds": duration}
    except Exception as exc:
        duration = time.perf_counter() - start
        return {"query": query, "results": [f"Web search error: {exc}"], "durationSeconds": duration}
