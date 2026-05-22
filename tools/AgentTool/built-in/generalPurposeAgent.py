"""General-purpose agent — mirrors src/tools/AgentTool/built-in/generalPurposeAgent.ts"""

AGENT_TYPE = "general-purpose"
WHEN_TO_USE = (
    "General-purpose agent with access to all tools. "
    "Use for complex multi-step tasks requiring implementation."
)

DEFINITION = {
    "agentType": AGENT_TYPE,
    "whenToUse": WHEN_TO_USE,
    "tools": [],
    "disallowedTools": [],
}
