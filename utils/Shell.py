"""Shell class — mirrors src/utils/Shell.ts"""
from __future__ import annotations
import asyncio
from typing import Optional


class Shell:
    def __init__(self, *, cwd: Optional[str] = None) -> None:
        self.cwd = cwd

    async def run(self, command: str, *, timeout: Optional[float] = 60) -> dict:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {"stdout": stdout.decode(), "stderr": stderr.decode(), "code": proc.returncode}
        except asyncio.TimeoutError:
            proc.kill()
            return {"stdout": "", "stderr": "Timeout", "code": -1}
