"""GrepTool prompt — mirrors src/tools/GrepTool/prompt.ts"""
GREP_TOOL_NAME = "Grep"

DESCRIPTION = "Search for a pattern in files"

GREP_PROMPT = """Use this tool to search for text patterns in files. It uses ripgrep for fast searching.
You can:
1. Search with literal strings or regex patterns
2. Limit results to specific file types
3. Search in specific directories

Results include file paths, line numbers, and matching content."""
