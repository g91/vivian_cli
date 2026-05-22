"""
Port of src/utils/nativeInstaller/packageManagers.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import sys
import re
import asyncio
import hashlib
import glob
import platform
from functools import lru_cache, wraps


PackageManager = Any


# Parses /etc/os-release to extract the distro ID and ID_LIKE fields.
getOsRelease: Any = None  # type: ignore
# Detects if the currently running vivian instance was installed via pacman
detectPacman: Any = None  # type: ignore
# Detects if the currently running vivian instance was installed via a .deb package
detectDeb: Any = None  # type: ignore
# Detects if the currently running vivian instance was installed via an RPM package
detectRpm: Any = None  # type: ignore
# Detects if the currently running vivian instance was installed via Alpine APK
detectApk: Any = None  # type: ignore
# Memoized function to detect which package manager installed vivian
getPackageManager: Any = None  # type: ignore


def isDistroFamily(osRelease, families):
    return (
    families.find(osRelease.id) or
    osRelease.idLike.some(lambda like: families.find(like))
    )


def detectMise():
    """Detects if the currently running vivian instance was installed via mise"""
    result = None
    result = None
    return result


def detectAsdf():
    """Detects if the currently running vivian instance was installed via asdf"""
    result = None
    result = None
    return result


def detectHomebrew():
    """Detects if the currently running vivian instance was installed via Homebrew"""
    result = None
    result = None
    return result


def detectWinget():
    """Detects if the currently running vivian instance was installed via winget"""
    result = None
    result = None
    return result

