"""Port of src/utils/permissions/bashClassifier.ts"""
from __future__ import annotations
from typing import Optional, List, Any

PROMPT_PREFIX = 'prompt:'


def extractPromptDescription(rule_content: Optional[str]) -> Optional[str]:
    """Extract a description from a prompt-style rule content. Returns None for non-prompt rules."""
    if rule_content is None:
        return None
    if rule_content.startswith(PROMPT_PREFIX):
        return rule_content[len(PROMPT_PREFIX):].strip() or None
    return None


def createPromptRuleContent(description: str) -> str:
    """Create a prompt-style rule content string from a description."""
    return f"{PROMPT_PREFIX} {description.strip()}"


def isClassifierPermissionsEnabled() -> bool:
    """Return whether classifier-based permissions are enabled. Always False in external builds."""
    return False


def getBashPromptDenyDescriptions(_context: Any) -> List[str]:
    """Get bash deny descriptions for classifier. Returns empty list in external builds."""
    return []


def getBashPromptAskDescriptions(_context: Any) -> List[str]:
    """Get bash ask descriptions for classifier. Returns empty list in external builds."""
    return []


def getBashPromptAllowDescriptions(_context: Any) -> List[str]:
    """Get bash allow descriptions for classifier. Returns empty list in external builds."""
    return []


async def classifyBashCommand(
    _command: str,
    _cwd: str,
    _descriptions: List[str],
    _behavior: str,
    _signal: Any,
    _is_non_interactive_session: bool,
) -> dict:
    """Classify a bash command. Returns disabled result in external builds."""
    return {
        'matches': False,
        'confidence': 'high',
        'reason': 'This feature is disabled',
    }


async def generateGenericDescription(
    _command: str,
    specific_description: Optional[str],
    _signal: Any,
) -> Optional[str]:
    """Generate a generic description for a command. Returns specific description if provided."""
    return specific_description or None
