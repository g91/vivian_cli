"""Port of src/utils/execSyncWrapper.ts."""
from __future__ import annotations

import subprocess
from typing import Any, Mapping, Optional


def _run_exec_sync(command: str, options: Optional[Mapping[str, Any]] = None):
    opts = dict(options or {})
    encoding = opts.pop("encoding", None)
    text = bool(encoding) or bool(opts.pop("text", False))
    if encoding and "errors" not in opts:
        opts["errors"] = "replace"
    cwd = opts.pop("cwd", None)
    shell = opts.pop("shell", True)
    return subprocess.check_output(
        command,
        shell=shell,
        cwd=cwd,
        text=text,
        encoding=encoding,
        **opts,
    )


def execSync_DEPRECATED(command, options=None):
    """@deprecated Use async alternatives when possible. Sync exec calls block the event loop.

Wrapped execSync with slow operation logging.
Use this instead of child_process execSync directly to detect performance issues.

@example
import { execSync_DEPRECATED } from './execSyncWrapper.js'
const result = execSync_DEPRECATED('git status', { encoding: 'utf8' })"""
    return _run_exec_sync(command, options)


exec_sync_deprecated = execSync_DEPRECATED

