"""WebFetchTool — mirrors src/tools/WebFetchTool/WebFetchTool.tsx"""
from __future__ import annotations
import re
import time
import urllib.request
import urllib.parse
from typing import Any, Dict, Optional

TOOL_NAME = "WebFetch"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["url", "prompt"],
    "properties": {
        "url": {"type": "string", "description": "URL to fetch"},
        "prompt": {"type": "string", "description": "What information to extract from the page"},
        "raw": {"type": "boolean", "description": "Return raw HTML instead of extracted text"},
        "max_length": {"type": "integer", "description": "Maximum response length in characters"},
    },
}

MAX_LENGTH = 20_000
_PROMPT_WORD_RE = re.compile(r"[A-Za-z0-9]{3,}")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")
_STOP_WORDS = {
    "about",
    "after",
    "before",
    "could",
    "find",
    "from",
    "into",
    "look",
    "page",
    "please",
    "show",
    "that",
    "this",
    "what",
    "when",
    "where",
    "which",
    "with",
}


async def description() -> str:
    return "Fetch content from a web page."


async def prompt() -> str:
    return (
        "Use this tool to fetch and read the content of a web page. "
        "Provide both the URL and a prompt describing what information to extract. "
        "Returns prompt-focused extracted text content rather than raw HTML."
    )


def userFacingName() -> str:
    return "Fetch"


def getToolUseSummary(input_data: Dict[str, Any]) -> str:
    return input_data.get("url", "")


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_prompt_keywords(prompt: str) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for match in _PROMPT_WORD_RE.finditer(prompt.lower()):
        word = match.group(0)
        if word in _STOP_WORDS:
            continue
        if word not in seen:
            seen.add(word)
            keywords.append(word)
    return keywords


def _candidate_chunks(text: str) -> list[str]:
    paragraphs = [_normalize_text(part) for part in _PARAGRAPH_SPLIT_RE.split(text) if _normalize_text(part)]
    if len(paragraphs) > 1:
        return paragraphs
    return [_normalize_text(part) for part in _SENTENCE_SPLIT_RE.split(text) if _normalize_text(part)]


def _apply_prompt_to_text(prompt: str, text: str, max_length: int) -> str:
    normalized_text = _normalize_text(text)
    if not prompt.strip() or not normalized_text:
        return normalized_text[:max_length]

    keywords = _extract_prompt_keywords(prompt)
    if not keywords:
        return normalized_text[:max_length]

    ranked: list[tuple[int, int, str]] = []
    for chunk in _candidate_chunks(text):
        lower_chunk = chunk.lower()
        matches = sum(1 for keyword in keywords if keyword in lower_chunk)
        if matches <= 0:
            continue
        density = sum(lower_chunk.count(keyword) for keyword in keywords)
        ranked.append((matches, density, chunk))

    if not ranked:
        return normalized_text[:max_length]

    ranked.sort(key=lambda item: (-item[0], -item[1], len(item[2])))
    return ranked[0][2][:max_length]


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    del context
    url = input_data.get("url", "")
    max_length = input_data.get("max_length", MAX_LENGTH)
    raw = input_data.get("raw", False)
    requested_prompt = input_data.get("prompt", "")
    start = time.perf_counter()

    if not url.startswith(("http://", "https://")):
        return {
            "error": "Only http:// and https:// URLs are supported",
            "bytes": 0,
            "code": 0,
            "codeText": "Invalid URL",
            "result": "",
            "durationMs": round((time.perf_counter() - start) * 1000),
            "url": url,
        }
    if not raw and not str(requested_prompt or "").strip():
        return {
            "error": "A non-empty prompt is required unless raw=True",
            "bytes": 0,
            "code": 0,
            "codeText": "Invalid Prompt",
            "result": "",
            "durationMs": round((time.perf_counter() - start) * 1000),
            "url": url,
        }

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; VivianBot/1.0)",
                "Accept": "text/html,application/xhtml+xml,*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            status_code = int(getattr(resp, "status", 200) or 200)
            status_text = str(getattr(resp, "reason", "OK") or "OK")
            charset = "utf-8"
            content_type = resp.getheader("Content-Type", "")
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].strip()
            body_bytes = resp.read(max_length * 2)
            body = body_bytes.decode(charset, errors="replace")

        if raw:
            result_text = body[:max_length]
            return {
                "bytes": len(body_bytes),
                "code": status_code,
                "codeText": status_text,
                "result": result_text,
                "content": result_text,
                "durationMs": round((time.perf_counter() - start) * 1000),
                "url": url,
                "prompt": requested_prompt,
            }

        # Simple HTML stripping
        text = re.sub(r"<script[^>]*>.*?</script>", "", body, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<(br|/p|/div|/li|/tr|/h[1-6])[^>]*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        result_text = _apply_prompt_to_text(requested_prompt, text, max_length)

        return {
            "bytes": len(body_bytes),
            "code": status_code,
            "codeText": status_text,
            "result": result_text,
            "content": result_text,
            "durationMs": round((time.perf_counter() - start) * 1000),
            "url": url,
            "prompt": requested_prompt,
        }

    except Exception as e:
        return {
            "error": str(e),
            "bytes": 0,
            "code": 0,
            "codeText": "Error",
            "result": "",
            "durationMs": round((time.perf_counter() - start) * 1000),
            "url": url,
            "prompt": requested_prompt,
        }
