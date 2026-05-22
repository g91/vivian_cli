"""GlobTool prompt — mirrors src/tools/GlobTool/prompt.ts"""
GLOB_TOOL_NAME = "Glob"

DESCRIPTION = "Find files matching a glob pattern"

GLOB_PROMPT = """Use this tool to find files matching a glob pattern. This is useful for:
1. Finding all files of a certain type (e.g., *.py, *.ts)
2. Finding files in specific directories (e.g., src/**/*.test.ts)
3. Discovering project structure

Results are sorted by modification time (newest first) and limited to 1000 results."""
