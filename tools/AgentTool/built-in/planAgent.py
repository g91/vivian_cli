"""Plan agent — mirrors src/tools/AgentTool/built-in/planAgent.ts"""

AGENT_TYPE = "Plan"
WHEN_TO_USE = "Create a structured implementation plan before writing code."

DEFINITION = {
    "agentType": AGENT_TYPE,
    "whenToUse": WHEN_TO_USE,
    "tools": ["Read", "Glob", "Grep", "Bash", "EnterPlanMode", "ExitPlanMode"],
    "disallowedTools": [],
}
