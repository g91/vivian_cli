"""vivian Code Guide agent — mirrors src/tools/AgentTool/built-in/vivianCodeGuideAgent.ts"""

AGENT_TYPE = "vivianCodeGuide"
WHEN_TO_USE = "Get guidance on how to use vivian Code effectively."

SYSTEM_PROMPT = """You are the vivian Code Guide agent. Your job is to help users understand
how to use vivian Code effectively, including its tools, workflows, and best practices.
"""

DEFINITION = {
    "agentType": AGENT_TYPE,
    "whenToUse": WHEN_TO_USE,
    "tools": ["Read", "Glob", "Grep"],
    "disallowedTools": ["Edit", "Write", "Bash"],
    "systemPrompt": SYSTEM_PROMPT,
}
