"""Explore agent — mirrors src/tools/AgentTool/built-in/exploreAgent.ts"""

AGENT_TYPE = "Explore"
WHEN_TO_USE = (
    "Fast read-only codebase exploration and Q&A subagent. "
    "Safe to call in parallel. Specify thoroughness: quick, medium, or thorough."
)

DEFINITION = {
    "agentType": AGENT_TYPE,
    "whenToUse": WHEN_TO_USE,
    "tools": ["Read", "Glob", "Grep", "Bash"],
    "disallowedTools": ["Edit", "Write"],
}
