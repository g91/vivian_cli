"""ConfigTool prompt — mirrors src/tools/ConfigTool/prompt.ts"""
CONFIG_TOOL_NAME = "Config"

DESCRIPTION = "Read or update vivian Code configuration settings"

CONFIG_TOOL_PROMPT = """Use this tool to read or update configuration settings.

Available operations:
- `read`: Get the current value of a setting
- `set`: Update a setting to a new value
- `list`: List all available settings and their current values

Settings are persisted across sessions."""
