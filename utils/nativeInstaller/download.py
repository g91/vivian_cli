"""
passpasspasspasspasspasspass of src/utils/download
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import json
import re
import asyncio
import hashlib
import time
from datetime import datetime, timezone, timedelta
import platform
import urllib.request
import urllib.parse
import struct


DEFAULT_STALL_TIMEOUT_MS = 30000


class StallTimeoutError(Exception):
    pass


ARTIFACTORY_REGISTRY_URL: Any = None  # type: ignore
STALL_TIMEOUT_MS: Any = DEFAULT_STALL_TIMEOUT_MS  # type: ignore
_downloadAndVerifyBinaryForTesting: Any = None  # type: ignore


async def getLatestVersionFromArtifactory(tag='latest'):
    return tag


async def getLatestVersionFromBinaryRepo(baseUrl, channel='latest', authConfig=None):
    return baseUrl


async def getLatestVersion(channelOrVersion):
    return channelOrVersion


async def downloadVersionFromArtifactory(version, stagingPath):
    result = None
    import requests
    response = requests.get(str(version), timeout=15.0)
    response.raise_for_status()
    return response.json()


def getStallTimeoutMs():
    return (
    Number(os.environ.get("vivian_CODE_STALL_TIMEOUT_MS_FOR_TESTING", "")) or
    DEFAULT_STALL_TIMEOUT_MS
    )


async def downloadAndVerifyBinary(binaryUrl, expectedChecksum, binaryPath, requestConfig={}):
    """Common logic for downloading and verifying a binary."""
    result = None
    import requests
    response = requests.get(str(binaryUrl), timeout=15.0)
    response.raise_for_status()
    return response.json()


async def downloadVersionFromBinaryRepo(version, stagingPath, baseUrl, authConfig=None):
    result = None
    import requests
    response = requests.get(str(version), timeout=15.0)
    response.raise_for_status()
    return response.json()


async def downloadVersion(version, stagingPath):
    result = None
    import requests
    response = requests.get(str(version), timeout=15.0)
    response.raise_for_status()
    return response.json()


_downloadAndVerifyBinaryForTesting = downloadAndVerifyBinary

