"""
Port of src/utils/codeIndexing.ts
"""
from __future__ import annotations

from typing import Literal, Optional
import re


CodeIndexingTool = Literal[
    "sourcegraph",
    "hound",
    "seagoat",
    "bloop",
    "gitloop",
    "cody",
    "aider",
    "continue",
    "github-copilot",
    "cursor",
    "tabby",
    "codeium",
    "tabnine",
    "augment",
    "windsurf",
    "aide",
    "pieces",
    "qodo",
    "amazon-q",
    "gemini",
    "vivian-context",
    "code-index-mcp",
    "local-code-search",
    "autodev-codebase",
    "openctx",
]


CLI_COMMAND_MAPPING: dict[str, CodeIndexingTool] = {
    "src": "sourcegraph",
    "cody": "cody",
    "aider": "aider",
    "tabby": "tabby",
    "tabnine": "tabnine",
    "augment": "augment",
    "pieces": "pieces",
    "qodo": "qodo",
    "aide": "aide",
    "hound": "hound",
    "seagoat": "seagoat",
    "bloop": "bloop",
    "gitloop": "gitloop",
    "q": "amazon-q",
    "gemini": "gemini",
}


MCP_SERVER_PATTERNS: tuple[tuple[re.Pattern[str], CodeIndexingTool], ...] = (
    (re.compile(r"^sourcegraph$", re.I), "sourcegraph"),
    (re.compile(r"^cody$", re.I), "cody"),
    (re.compile(r"^openctx$", re.I), "openctx"),
    (re.compile(r"^aider$", re.I), "aider"),
    (re.compile(r"^continue$", re.I), "continue"),
    (re.compile(r"^github[-_]?copilot$", re.I), "github-copilot"),
    (re.compile(r"^copilot$", re.I), "github-copilot"),
    (re.compile(r"^cursor$", re.I), "cursor"),
    (re.compile(r"^tabby$", re.I), "tabby"),
    (re.compile(r"^codeium$", re.I), "codeium"),
    (re.compile(r"^tabnine$", re.I), "tabnine"),
    (re.compile(r"^augment[-_]?code$", re.I), "augment"),
    (re.compile(r"^augment$", re.I), "augment"),
    (re.compile(r"^windsurf$", re.I), "windsurf"),
    (re.compile(r"^aide$", re.I), "aide"),
    (re.compile(r"^codestory$", re.I), "aide"),
    (re.compile(r"^pieces$", re.I), "pieces"),
    (re.compile(r"^qodo$", re.I), "qodo"),
    (re.compile(r"^amazon[-_]?q$", re.I), "amazon-q"),
    (re.compile(r"^gemini[-_]?code[-_]?assist$", re.I), "gemini"),
    (re.compile(r"^gemini$", re.I), "gemini"),
    (re.compile(r"^hound$", re.I), "hound"),
    (re.compile(r"^seagoat$", re.I), "seagoat"),
    (re.compile(r"^bloop$", re.I), "bloop"),
    (re.compile(r"^gitloop$", re.I), "gitloop"),
    (re.compile(r"^vivian[-_]?context$", re.I), "vivian-context"),
    (re.compile(r"^code[-_]?index[-_]?mcp$", re.I), "code-index-mcp"),
    (re.compile(r"^code[-_]?index$", re.I), "code-index-mcp"),
    (re.compile(r"^local[-_]?code[-_]?search$", re.I), "local-code-search"),
    (re.compile(r"^codebase$", re.I), "autodev-codebase"),
    (re.compile(r"^autodev[-_]?codebase$", re.I), "autodev-codebase"),
    (re.compile(r"^code[-_]?context$", re.I), "vivian-context"),
)


def detectCodeIndexingFromCommand(command):
    """Detects if a bash command is using a code indexing CLI tool.

@param command - The full bash command string
@returns The code indexing tool identifier, or undefined if not a code indexing command

@example
detectCodeIndexingFromCommand('src search "pattern"') // returns 'sourcegraph'
detectCodeIndexingFromCommand('cody chat --message "help"') // returns 'cody'
detectCodeIndexingFromCommand('ls -la') // returns undefined"""
    trimmed = command.strip()
    if not trimmed:
        return None
    parts = re.split(r"\s+", trimmed)
    first_word = parts[0].lower()
    if first_word in {"npx", "bunx"}:
        second_word = parts[1].lower() if len(parts) > 1 else None
        if second_word:
            return CLI_COMMAND_MAPPING.get(second_word)
        return None
    return CLI_COMMAND_MAPPING.get(first_word)


def detectCodeIndexingFromMcpTool(toolName):
    """Detects if an MCP tool is from a code indexing server.

@param toolName - The MCP tool name (format: mcp__serverName__toolName)
@returns The code indexing tool identifier, or undefined if not a code indexing tool

@example
detectCodeIndexingFromMcpTool('mcp__sourcegraph__search') // returns 'sourcegraph'
detectCodeIndexingFromMcpTool('mcp__cody__chat') // returns 'cody'
detectCodeIndexingFromMcpTool('mcp__filesystem__read') // returns undefined"""
    if not toolName.startswith("mcp__"):
        return None
    parts = toolName.split("__")
    if len(parts) < 3:
        return None
    server_name = parts[1]
    if not server_name:
        return None
    return detectCodeIndexingFromMcpServerName(server_name)


def detectCodeIndexingFromMcpServerName(serverName):
    """Detects if an MCP server name corresponds to a code indexing tool.

@param serverName - The MCP server name
@returns The code indexing tool identifier, or undefined if not a code indexing server

@example
detectCodeIndexingFromMcpServerName('sourcegraph') // returns 'sourcegraph'
detectCodeIndexingFromMcpServerName('filesystem') // returns undefined"""
    for pattern, tool in MCP_SERVER_PATTERNS:
        if pattern.search(serverName):
            return tool
    return None


detect_code_indexing_from_command = detectCodeIndexingFromCommand
detect_code_indexing_from_mcp_tool = detectCodeIndexingFromMcpTool
detect_code_indexing_from_mcp_server_name = detectCodeIndexingFromMcpServerName

