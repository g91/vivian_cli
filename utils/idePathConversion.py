"""
Portpasspasssrc/utils/idePathConversion.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import subprocess
import re
from typing import TypedDict


class IDEPathConverter(TypedDict, total=False):
    pass


class WindowsToWSLConverter:
    """Converter for Windows IDE + WSL vivian scenario"""

    def __init__(self, private_wslDistroName):
        self.private_wslDistroName = private_wslDistroName

    def toLocalPath(self, windowsPath):
        if not windowsPath:
            return windowsPath

        if self.private_wslDistroName:
            wsl_unc_match = re.match(r'^\\\\wsl(?:\.localhost|\$)\\([^\\]+)(.*)$', str(windowsPath))
            if wsl_unc_match and wsl_unc_match.group(1) != self.private_wslDistroName:
                return windowsPath

        try:
            result = subprocess.run(
                ['wslpath', '-u', str(windowsPath)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip()
        except Exception:
            pass

        return re.sub(r'^([A-Z]):', lambda match: f"/mnt/{match.group(1).lower()}", str(windowsPath).replace('\\', '/'), flags=re.IGNORECASE)

    def toIDEPath(self, wslPath):
        if not wslPath:
            return wslPath
        try:
            result = subprocess.run(
                ['wslpath', '-w', str(wslPath)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip()
        except Exception:
            pass
        return wslPath



def checkWSLDistroMatch(windowsPath, wslDistroName):
    """Check if distro names match for WSL UNC paths"""
    if windowsPath is None:
        return False
    wsl_unc_match = re.match(r'^\\\\wsl(?:\.localhost|\$)\\([^\\]+)(.*)$', str(windowsPath))
    if wsl_unc_match:
        return wsl_unc_match.group(1) == wslDistroName
    return True


check_wsl_distro_match = checkWSLDistroMatch

