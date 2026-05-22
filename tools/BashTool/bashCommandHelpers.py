"""
BashTool command helpers — mirrors src/tools/BashTool/bashCommandHelpers.ts
"""
from __future__ import annotations
import re
from typing import Any, Callable, Dict, List, Optional


def segmentedCommandPermissionResult(
    input_data: Dict[str, Any],
    segments: List[str],
    bashToolHasPermissionFn: Callable[[Dict[str, Any]], Dict[str, Any]],
    checkers: Optional[Dict[str, Callable]] = None,
) -> Dict[str, Any]:
    """
    Check permissions for a command that has been split into segments.
    Returns a permission result dict.
    """
    if checkers is None:
        checkers = {}

    isNormalizedCdCommand = checkers.get("isNormalizedCdCommand", lambda c: c.startswith("cd ") or c == "cd")
    isNormalizedGitCommand = checkers.get("isNormalizedGitCommand", lambda c: c.startswith("git ") or c == "git")

    # Check for multiple cd commands across all segments
    cdCommands = [seg for seg in segments if isNormalizedCdCommand(seg.strip())]
    if len(cdCommands) > 1:
        decisionReason = {
            "type": "other",
            "reason": "Multiple directory changes in one command require approval for clarity",
        }
        return {
            "behavior": "ask",
            "decisionReason": decisionReason,
            "message": f"Permission required: {decisionReason['reason']}",
        }

    # Check for cd+git cross-segment pattern
    hasCd = False
    hasGit = False
    for segment in segments:
        subcommands = re.split(r"[;&]", segment)
        for sub in subcommands:
            trimmed = sub.strip()
            if isNormalizedCdCommand(trimmed):
                hasCd = True
            if isNormalizedGitCommand(trimmed):
                hasGit = True

    if hasCd and hasGit:
        decisionReason = {
            "type": "other",
            "reason": "Compound commands with cd and git require approval to prevent bare repository attacks",
        }
        return {
            "behavior": "ask",
            "decisionReason": decisionReason,
            "message": f"Permission required: {decisionReason['reason']}",
        }

    # Check each segment independently
    for segment in segments:
        segInput = {**input_data, "command": segment}
        result = bashToolHasPermissionFn(segInput)
        if result.get("behavior") != "allow":
            return result

    return {
        "behavior": "allow",
        "updatedInput": input_data,
        "decisionReason": {"type": "other", "reason": "All segments allowed"},
    }
