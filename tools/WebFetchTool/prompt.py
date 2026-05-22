"""WebFetchTool prompt — mirrors src/tools/WebFetchTool/prompt.ts"""
WEB_FETCH_TOOL_NAME = "WebFetch"

DESCRIPTION = "Fetch content from a URL"

WEB_FETCH_PROMPT = """Use this tool to fetch content from a URL. This is useful for:
1. Reading documentation
2. Checking API references
3. Fetching data from web services

Provide both a URL and a prompt describing what information to extract.
Content is returned as prompt-focused plain text (HTML is stripped).
Maximum content length: 20,000 characters."""
