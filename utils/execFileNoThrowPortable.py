"""
Port of src/utils/execFileNoThrowPortable.ts
"""
from __future__ import annotations

from typing import Any, Dict
import subprocess

from .cwd import get_cwd


ExecSyncOptions = Dict[str, Any]
MS_IN_SECOND = 1000
SECONDS_IN_MINUTE = 60


def execSyncWithDefaults_DEPRECATED(command, optionsOrAbortSignal=None, timeout = 10 * SECONDS_IN_MINUTE * MS_IN_SECOND):
    """@deprecated Use `execa` directly with `{ shell: true, reject: false }` for non-blocking execution.
Sync exec calls block the event loop and cause performance issues."""
    if optionsOrAbortSignal is None:
        options: ExecSyncOptions = {}
    elif isinstance(optionsOrAbortSignal, dict):
        options = dict(optionsOrAbortSignal)
    else:
        options = {
            "abortSignal": optionsOrAbortSignal,
            "timeout": timeout,
        }

    abort_signal = options.get("abortSignal")
    final_timeout = options.get("timeout", 10 * SECONDS_IN_MINUTE * MS_IN_SECOND)
    input_text = options.get("input")
    stdio = options.get("stdio", ["ignore", "pipe", "pipe"])

    if abort_signal is not None:
        throw_if_aborted = getattr(abort_signal, "throwIfAborted", None)
        if callable(throw_if_aborted):
            throw_if_aborted()

    stdout_pipe = subprocess.PIPE
    stderr_pipe = subprocess.PIPE
    run_kwargs: ExecSyncOptions = {}
    if isinstance(stdio, (list, tuple)) and len(stdio) >= 3:
        stdout_pipe = subprocess.PIPE if stdio[1] == "pipe" else None
        stderr_pipe = subprocess.PIPE if stdio[2] == "pipe" else None
        if input_text is None:
            run_kwargs["stdin"] = subprocess.DEVNULL if stdio[0] == "ignore" else None

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=get_cwd(),
            env=None,
            input=input_text,
            text=True,
            stdout=stdout_pipe,
            stderr=stderr_pipe,
            timeout=final_timeout / 1000,
            check=False,
            **run_kwargs,
        )
        stdout = result.stdout if isinstance(result.stdout, str) else ""
        trimmed = stdout.strip()
        return trimmed or None
    except Exception:
        return None


exec_sync_with_defaults_deprecated = execSyncWithDefaults_DEPRECATED

