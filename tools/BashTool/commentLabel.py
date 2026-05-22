"""
Extract bash comment labels — mirrors src/tools/BashTool/commentLabel.ts
"""
from __future__ import annotations
from typing import Optional


def extractBashCommentLabel(command: str) -> Optional[str]:
    """
    If the first line of a bash command is a `# comment` (not a `#!` shebang),
    return the comment text stripped of the `#` prefix. Otherwise None.
    """
    nl = command.find("\n")
    firstLine = (command if nl == -1 else command[:nl]).strip()
    if not firstLine.startswith("#") or firstLine.startswith("#!"):
        return None
    stripped = firstLine.lstrip("#").lstrip()
    return stripped or None
