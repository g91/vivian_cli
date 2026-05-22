"""execFile wrapper that never throws — mirrors src/utils/execFileNoThrow.ts"""
from __future__ import annotations

import asyncio
import subprocess
from typing import Optional


async def exec_file_no_throw(
    file: str,
    args: list[str],
    *,
    timeout: Optional[float] = 600,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    stdin_input: Optional[str] = None,
) -> dict:
    """Run a subprocess and return result dict without raising on non-zero exit.

    Returns {'stdout': str, 'stderr': str, 'code': int, 'error': Optional[str]}.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            file,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if stdin_input is not None else asyncio.subprocess.DEVNULL,
            cwd=cwd,
            env=env,
        )
        stdin_bytes = stdin_input.encode() if stdin_input else None
        stdout_data, stderr_data = await asyncio.wait_for(
            proc.communicate(stdin_bytes), timeout=timeout
        )
        return {
            "stdout": stdout_data.decode(errors="replace"),
            "stderr": stderr_data.decode(errors="replace"),
            "code": proc.returncode or 0,
        }
    except asyncio.TimeoutError:
        return {"stdout": "", "stderr": "Process timed out", "code": -1, "error": "timeout"}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "code": -1, "error": str(e)}


def exec_file_no_throw_sync(
    file: str,
    args: list[str],
    *,
    timeout: Optional[float] = 600,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    stdin_input: Optional[str] = None,
) -> dict:
    """Synchronous version of exec_file_no_throw."""
    try:
        result = subprocess.run(
            [file] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
            input=stdin_input,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Process timed out", "code": -1, "error": "timeout"}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "code": -1, "error": str(e)}
