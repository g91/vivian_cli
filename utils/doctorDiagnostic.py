"""
    passpasspass of src/utils/doctorDiagnostic.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import sys
import json
import asyncio
import hashlib
import glob
import platform
from enum import Enum, auto
import struct


InstallationType = Any
DiagnosticInfo = Dict[str, Any]


def getNormalizedPaths():
    invokedPath = process.argv[1] or ''
    execPath = process.execPath or process.argv[0] or ''
    # On Windows, convert backslashes to forward slashes for consistent path matching
    if getPlatform() == 'windows':
        invokedPath = invokedPath.split(win32.sep).join(posix.sep)
        execPath = execPath.split(win32.sep).join(posix.sep)
    return [invokedPath, execPath]


async def getCurrentInstallationType():
    result = None
    _result: dict = {}
    # Implement getCurrentInstallationType
    return _result


async def getInstallationPath():
    result = None
    _result: dict = {}
    # Implement getInstallationPath
    return _result


def getInvokedBinary():
    try:
        # For bundled/compiled executables, show the actual binary path
        if isInBundledMode():
            return process.execPath or 'unknown'
        # For npm/development, show the script path
        return process.argv[1] or 'unknown'
    except Exception:
        return 'unknown'


async def detectMultipleInstallations():
    type: string; path


async def detectConfigurationIssues(type):
    issue: string; fix


def detectLinuxGlobPatternWarnings():
    issue
    fix


async def getDoctorDiagnostic():
    result = None
    _result: dict = {}
    # Implement getDoctorDiagnostic
    return _result

