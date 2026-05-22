"""Port of src/utils/shell/powershellDetection.ts."""
from __future__ import annotations

import os
from typing import Literal, Optional

from ..platform import get_platform
from ..which import which


PowerShellEdition = Literal["core", "desktop"]

_cached_powershell_path: Optional[str] | None = None
_cache_initialized = False


async def probePath(p: str) -> Optional[str]:
    try:
        return p if os.path.isfile(p) else None
    except Exception:
        return None


async def findPowerShell() -> Optional[str]:
    """Attempts to find PowerShell on the system via PATH.
Prefers pwsh (PowerShell Core 7+), falls back to powershell (5.1).

On Linux, if PATH resolves to a snap launcher (/snap/…) — directly or
via a symlink chain like /usr/bin/pwsh → /snap/bin/pwsh — probe known
apt/rpm install locations instead: the snap launcher can hang in
subprocesses while snapd initializes confinement, but the underlying
binary at /opt/microsoft/powershell/7/pwsh is reliable. On
Windows/macOS, PATH is sufficient."""
    pwsh_path = await which("pwsh")
    if pwsh_path:
        if get_platform() == "linux":
            resolved = os.path.realpath(pwsh_path)
            if pwsh_path.startswith("/snap/") or resolved.startswith("/snap/"):
                direct = await probePath("/opt/microsoft/powershell/7/pwsh")
                if direct is None:
                    direct = await probePath("/usr/bin/pwsh")
                if direct is not None:
                    direct_resolved = os.path.realpath(direct)
                    if not direct.startswith("/snap/") and not direct_resolved.startswith("/snap/"):
                        return direct
        return pwsh_path

    powershell_path = await which("powershell")
    if powershell_path:
        return powershell_path

    return None


async def getCachedPowerShellPath() -> Optional[str]:
    """Gets the cached PowerShell path. Returns a memoized promise that
resolves to the PowerShell executable path or null."""
    global _cached_powershell_path, _cache_initialized
    if not _cache_initialized:
        _cached_powershell_path = await findPowerShell()
        _cache_initialized = True
    return _cached_powershell_path


async def getPowerShellEdition() -> Optional[PowerShellEdition]:
    """Infers the PowerShell edition from the binary name without spawning.
- `pwsh` / `pwsh.exe` → 'core' (PowerShell 7+: supports `&&`, `||`, `?:`, `??`)
- `powershell` / `powershell.exe` → 'desktop' (Windows PowerShell 5.1:
no pipeline chain operators, stderr-sets-$? bug, UTF-16 default encoding)

PowerShell 6 (also `pwsh`, no `&&`) has been EOL since 2020 and is not
a realistic install target, so 'core' safely implies 7+ semantics.

Used by the tool prompt to give version-appropriate syntax guidance so
the model doesn't emit `cmd1 && cmd2` on 5.1 (parser error) or avoid
`&&` on 7+ where it's the correct short-circuiting operator."""
    path = await getCachedPowerShellPath()
    if not path:
        return None
    base = os.path.basename(path).lower().removesuffix(".exe")
    return "core" if base == "pwsh" else "desktop"


def resetPowerShellCache() -> None:
    """Resets the cached PowerShell path. Only for testing."""
    global _cached_powershell_path, _cache_initialized
    _cached_powershell_path = None
    _cache_initialized = False

