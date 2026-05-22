"""Verification agent — mirrors src/tools/AgentTool/built-in/verificationAgent.ts"""
from ..constants import VERIFICATION_AGENT_TYPE

AGENT_TYPE = VERIFICATION_AGENT_TYPE
WHEN_TO_USE = (
    "Verify correctness of an implementation by running tests and checks. "
    "Read-heavy — runs tests and reports results."
)

DEFINITION = {
    "agentType": AGENT_TYPE,
    "whenToUse": WHEN_TO_USE,
    "tools": ["Read", "Bash", "Grep", "Glob"],
    "disallowedTools": [],
}
