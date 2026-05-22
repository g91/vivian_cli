"""MCPTool prompt — mirrors src/tools/MCPTool/prompt.ts"""
MCP_TOOL_NAME = "MCP"

DESCRIPTION = "Call a Model Context Protocol tool"

MCP_PROMPT = """Use this tool to call MCP (Model Context Protocol) tools.
MCP tools provide access to external services, APIs, and data sources.
Each MCP server exposes its own set of tools with specific input schemas.

Available MCP servers and their tools are listed in the system context."""
