"""Port of src/utils/deepLink/registerProtocol.ts."""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
import time
from pathlib import Path

from ..debug import logForDebugging
from ..envUtils import get_vivian_config_home_dir
from ..settings.settings import getInitialSettings
from ..which import which
from ..xdg import getUserBinDir, getXDGDataHome
from .parseDeepLink import DEEP_LINK_PROTOCOL


MACOS_BUNDLE_ID = "com.anthropic.vivian-code-url-handler"
APP_NAME = "vivian Code URL Handler"
DESKTOP_FILE_NAME = "vivian-code-url-handler.desktop"
MACOS_APP_NAME = "vivian Code URL Handler.app"
MACOS_APP_DIR = str(Path.home() / "Applications" / MACOS_APP_NAME)
MACOS_SYMLINK_PATH = str(Path(MACOS_APP_DIR) / "Contents" / "MacOS" / "vivian")
WINDOWS_REG_KEY = rf"HKEY_CURRENT_USER\Software\Classes\{DEEP_LINK_PROTOCOL}"
WINDOWS_COMMAND_KEY = rf"{WINDOWS_REG_KEY}\shell\open\command"
FAILURE_BACKOFF_MS = 24 * 60 * 60 * 1000


def linuxDesktopPath() -> str:
    return str(Path(getXDGDataHome()) / "applications" / DESKTOP_FILE_NAME)


def linuxExecLine(vivianPath: str) -> str:
    return f'Exec="{vivianPath}" --handle-uri %u'


def windowsCommandValue(vivianPath: str) -> str:
    return f'"{vivianPath}" --handle-uri "%1"'


async def registerMacos(vivianPath: str):
    contents_dir = Path(MACOS_APP_DIR) / "Contents"
    try:
        shutil.rmtree(MACOS_APP_DIR)
    except FileNotFoundError:
        _missing_app_dir = True
    Path(MACOS_SYMLINK_PATH).parent.mkdir(parents=True, exist_ok=True)
    info_plist = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\"><dict>
<key>CFBundleIdentifier</key><string>{MACOS_BUNDLE_ID}</string>
<key>CFBundleName</key><string>{APP_NAME}</string>
<key>CFBundleExecutable</key><string>vivian</string>
<key>CFBundleVersion</key><string>1.0</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>LSBackgroundOnly</key><true/>
<key>CFBundleURLTypes</key><array><dict>
<key>CFBundleURLName</key><string>vivian Code Deep Link</string>
<key>CFBundleURLSchemes</key><array><string>{DEEP_LINK_PROTOCOL}</string></array>
</dict></array></dict></plist>"""
    contents_dir.mkdir(parents=True, exist_ok=True)
    (contents_dir / "Info.plist").write_text(info_plist, encoding="utf-8")
    os.symlink(vivianPath, MACOS_SYMLINK_PATH)
    logForDebugging(f"Registered {DEEP_LINK_PROTOCOL}:// protocol handler at {MACOS_APP_DIR}")


async def registerLinux(vivianPath: str):
    desktop_path = Path(linuxDesktopPath())
    desktop_path.parent.mkdir(parents=True, exist_ok=True)
    desktop_entry = (
        f"[Desktop Entry]\n"
        f"Name={APP_NAME}\n"
        f"Comment=Handle {DEEP_LINK_PROTOCOL}:// deep links for vivian Code\n"
        f"{linuxExecLine(vivianPath)}\n"
        "Type=Application\n"
        "NoDisplay=true\n"
        f"MimeType=x-scheme-handler/{DEEP_LINK_PROTOCOL};\n"
    )
    desktop_path.write_text(desktop_entry, encoding="utf-8")
    xdg_mime = await which("xdg-mime")
    if xdg_mime:
        proc = await asyncio.create_subprocess_exec(
            xdg_mime,
            "default",
            DESKTOP_FILE_NAME,
            f"x-scheme-handler/{DEEP_LINK_PROTOCOL}",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        code = await proc.wait()
        if code != 0:
            raise RuntimeError(f"xdg-mime exited with code {code}")
    logForDebugging(f"Registered {DEEP_LINK_PROTOCOL}:// protocol handler at {desktop_path}")


async def registerWindows(vivianPath: str):
    raise RuntimeError("Windows protocol registration is not supported in this Python environment")


async def registerProtocolHandler(vivianPath=None):
    resolved = vivianPath or await resolvevivianPath()
    if sys.platform == "darwin":
        await registerMacos(resolved)
    elif sys.platform == "linux":
        await registerLinux(resolved)
    elif sys.platform == "win32":
        await registerWindows(resolved)
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")


async def resolvevivianPath():
    binary_name = "vivian.exe" if sys.platform == "win32" else "vivian"
    stable_path = str(Path(getUserBinDir()) / binary_name)
    if Path(stable_path).exists():
        return stable_path
    return sys.executable


async def isProtocolHandlerCurrent(vivianPath):
    try:
        if sys.platform == "darwin":
            return os.readlink(MACOS_SYMLINK_PATH) == vivianPath
        if sys.platform == "linux":
            return linuxExecLine(vivianPath) in Path(linuxDesktopPath()).read_text(encoding="utf-8")
        return False
    except Exception:
        return False


async def ensureDeepLinkProtocolRegistered():
    settings = getInitialSettings() or {}
    if settings.get("disableDeepLinkRegistration") == "disable":
        return
    vivian_path = await resolvevivianPath()
    if await isProtocolHandlerCurrent(vivian_path):
        return
    failure_marker = Path(get_vivian_config_home_dir()) / ".deep-link-register-failed"
    try:
        if failure_marker.exists() and (time.time() - failure_marker.stat().st_mtime) * 1000 < FAILURE_BACKOFF_MS:
            return
    except Exception:
        _marker_stat_failed = True
    try:
        await registerProtocolHandler(vivian_path)
        logForDebugging("Auto-registered vivian-cli:// deep link protocol handler")
        failure_marker.unlink(missing_ok=True)
    except Exception as error:
        logForDebugging(f"Failed to auto-register deep link protocol handler: {error}", level="warn")
        try:
            failure_marker.parent.mkdir(parents=True, exist_ok=True)
            failure_marker.write_text("", encoding="utf-8")
        except Exception:
            _marker_write_failed = True


register_protocol_handler = registerProtocolHandler
resolve_vivian_path = resolvevivianPath
is_protocol_handler_current = isProtocolHandlerCurrent
ensure_deep_link_protocol_registered = ensureDeepLinkProtocolRegistered

