"""Command lookup — mirrors src/utils/which.ts"""
from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Optional


async def which(command: str) -> Optional[str]:
    """Find the full path to a command executable (async)."""
    return which_sync(command)


def which_sync(command: str) -> Optional[str]:
    """Find the full path to a command executable (synchronous)."""
    return shutil.which(command)


whichSync = which_sync
