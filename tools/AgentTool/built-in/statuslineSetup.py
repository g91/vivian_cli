"""Statusline setup agent — mirrors src/tools/AgentTool/built-in/statuslineSetup.ts"""
from __future__ import annotations


def getStatuslineSetupPrompt() -> str:
    return "Set up the terminal statusline for the vivian Code session."


AGENT_TYPE = "statusline-setup"
WHEN_TO_USE = "Set up and configure the terminal statusline display."

DEFINITION = {
    "agentType": AGENT_TYPE,
    "whenToUse": WHEN_TO_USE,
    "tools": ["Bash"],
    "disallowedTools": [],
}
