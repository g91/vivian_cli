"""
Shared ripgrep wrapper — mirrors src/tools/shared/ripgrep.ts
"""
from __future__ import annotations
import asyncio
import json
import os
import shutil
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RipgrepMatch:
    filePath: str
    lineNumber: int
    lineText: str
    submatches: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RipgrepResult:
    matches: List[RipgrepMatch]
    truncated: bool
    numMatches: int


def _findRg() -> Optional[str]:
    rg = shutil.which("rg")
    if rg:
        return rg
    vscode_rg_paths = [
        "/snap/code-insiders/current/usr/share/code-insiders/resources/app/node_modules/@vscode/ripgrep/bin/rg",
        "/usr/share/code/resources/app/node_modules/@vscode/ripgrep/bin/rg",
    ]
    for p in vscode_rg_paths:
        if os.path.exists(p):
            return p
    return None


async def runRipgrep(
    pattern: str,
    searchPath: str,
    flags: Optional[List[str]] = None,
    maxResults: int = 1000,
) -> RipgrepResult:
    """Run ripgrep and return structured results."""
    rg = _findRg()
    if not rg:
        return RipgrepResult(matches=[], truncated=False, numMatches=0)

    cmd = [rg, "--json"]
    if flags:
        cmd.extend(flags)
    cmd.extend([pattern, searchPath])

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        stdout = stdout_bytes.decode("utf-8", errors="replace")
    except (asyncio.TimeoutError, OSError):
        return RipgrepResult(matches=[], truncated=False, numMatches=0)

    matches: List[RipgrepMatch] = []
    for line in stdout.splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "match":
            continue
        data = obj.get("data", {})
        filePath = data.get("path", {}).get("text", "")
        lineNumber = data.get("line_number", 0)
        lineText = data.get("lines", {}).get("text", "")
        submatches = data.get("submatches", [])
        matches.append(RipgrepMatch(
            filePath=filePath,
            lineNumber=lineNumber,
            lineText=lineText,
            submatches=submatches,
        ))

    truncated = len(matches) > maxResults
    return RipgrepResult(
        matches=matches[:maxResults],
        truncated=truncated,
        numMatches=len(matches),
    )
