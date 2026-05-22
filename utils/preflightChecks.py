"""
passpass of src/utils/preflightChecks
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import sys
import json
import asyncio
import time
from datetime import datetime, timezone, timedelta
import base64
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from typing import TypedDict
import ssl


class PreflightCheckResult(TypedDict, total=False):
    success: bool
    error: str
    sslHint: str


class PreflightStepProps(TypedDict, total=False):
    onSuccess: Any


async def checkEndpoints():
    result = True
    _enabled = True
    return _enabled


def PreflightStep(t0):
    result = None
    _input = t0
    _output = _input if _input is not None else {}
    return _output


def _temp():
    return process.exit(1)

