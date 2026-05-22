"""Port of src/utils/ide.ts."""
from __future__ import annotations

import asyncio
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from ..bootstrap.state import getIsScrollDraining, getOriginalCwd
from .debug import log_error
from .env import env
from .envDynamic import envDynamic
from .envUtils import get_vivian_config_home_dir, is_env_truthy
from .execFileNoThrow import exec_file_no_throw, exec_file_no_throw_sync
from .genericProcessUtils import getAncestorPidsAsync, getProcessCommand
from .jetbrains import isJetBrainsPluginInstalledCached
from .platform import get_platform


LockfileJsonContent = Dict[str, Any]
IdeLockfileInfo = Dict[str, Any]
DetectedIDEInfo = Dict[str, Any]
IdeType = str
IdeConfig = Dict[str, Any]


class IDEExtensionInstallationStatus(TypedDict, total=False):
    installed: bool
    error: Optional[str]
    installedVersion: Optional[str]
    ideType: Optional[IdeType]


supportedIdeConfigs: Dict[IdeType, IdeConfig] = {
    "cursor": {"ideKind": "vscode", "displayName": "Cursor", "processKeywordsMac": ["Cursor Helper", "Cursor.app"], "processKeywordsWindows": ["cursor.exe"], "processKeywordsLinux": ["cursor"]},
    "windsurf": {"ideKind": "vscode", "displayName": "Windsurf", "processKeywordsMac": ["Windsurf Helper", "Windsurf.app"], "processKeywordsWindows": ["windsurf.exe"], "processKeywordsLinux": ["windsurf"]},
    "vscode": {"ideKind": "vscode", "displayName": "VS Code", "processKeywordsMac": ["Visual Studio Code", "Code Helper"], "processKeywordsWindows": ["code.exe"], "processKeywordsLinux": ["code"]},
    "intellij": {"ideKind": "jetbrains", "displayName": "IntelliJ IDEA", "processKeywordsMac": ["IntelliJ IDEA"], "processKeywordsWindows": ["idea64.exe"], "processKeywordsLinux": ["idea", "intellij"]},
    "pycharm": {"ideKind": "jetbrains", "displayName": "PyCharm", "processKeywordsMac": ["PyCharm"], "processKeywordsWindows": ["pycharm64.exe"], "processKeywordsLinux": ["pycharm"]},
    "webstorm": {"ideKind": "jetbrains", "displayName": "WebStorm", "processKeywordsMac": ["WebStorm"], "processKeywordsWindows": ["webstorm64.exe"], "processKeywordsLinux": ["webstorm"]},
    "phpstorm": {"ideKind": "jetbrains", "displayName": "PhpStorm", "processKeywordsMac": ["PhpStorm"], "processKeywordsWindows": ["phpstorm64.exe"], "processKeywordsLinux": ["phpstorm"]},
    "rubymine": {"ideKind": "jetbrains", "displayName": "RubyMine", "processKeywordsMac": ["RubyMine"], "processKeywordsWindows": ["rubymine64.exe"], "processKeywordsLinux": ["rubymine"]},
    "clion": {"ideKind": "jetbrains", "displayName": "CLion", "processKeywordsMac": ["CLion"], "processKeywordsWindows": ["clion64.exe"], "processKeywordsLinux": ["clion"]},
    "goland": {"ideKind": "jetbrains", "displayName": "GoLand", "processKeywordsMac": ["GoLand"], "processKeywordsWindows": ["goland64.exe"], "processKeywordsLinux": ["goland"]},
    "rider": {"ideKind": "jetbrains", "displayName": "Rider", "processKeywordsMac": ["Rider"], "processKeywordsWindows": ["rider64.exe"], "processKeywordsLinux": ["rider"]},
    "datagrip": {"ideKind": "jetbrains", "displayName": "DataGrip", "processKeywordsMac": ["DataGrip"], "processKeywordsWindows": ["datagrip64.exe"], "processKeywordsLinux": ["datagrip"]},
    "appcode": {"ideKind": "jetbrains", "displayName": "AppCode", "processKeywordsMac": ["AppCode"], "processKeywordsWindows": ["appcode.exe"], "processKeywordsLinux": ["appcode"]},
    "dataspell": {"ideKind": "jetbrains", "displayName": "DataSpell", "processKeywordsMac": ["DataSpell"], "processKeywordsWindows": ["dataspell64.exe"], "processKeywordsLinux": ["dataspell"]},
    "aqua": {"ideKind": "jetbrains", "displayName": "Aqua", "processKeywordsMac": ["Aqua"], "processKeywordsWindows": ["aqua64.exe"], "processKeywordsLinux": ["aqua"]},
    "gateway": {"ideKind": "jetbrains", "displayName": "Gateway", "processKeywordsMac": ["Gateway"], "processKeywordsWindows": ["gateway64.exe"], "processKeywordsLinux": ["gateway"]},
    "fleet": {"ideKind": "jetbrains", "displayName": "Fleet", "processKeywordsMac": ["Fleet"], "processKeywordsWindows": ["fleet.exe"], "processKeywordsLinux": ["fleet"]},
    "androidstudio": {"ideKind": "jetbrains", "displayName": "Android Studio", "processKeywordsMac": ["Android Studio"], "processKeywordsWindows": ["studio64.exe"], "processKeywordsLinux": ["android-studio"]},
}

_cached_running_ides: Optional[List[IdeType]] = None
_current_ide_search_generation = 0
EXTENSION_ID = "anthropic.vivian-code-internal" if os.environ.get("USER_TYPE") == "ant" else "anthropic.vivian-code"


@lru_cache(maxsize=1)
def isSupportedVSCodeTerminal() -> bool:
    return isVSCodeIde(getattr(env, "terminal", None))


@lru_cache(maxsize=1)
def isSupportedJetBrainsTerminal() -> bool:
    return isJetBrainsIde(getattr(envDynamic, "terminal", None))


@lru_cache(maxsize=1)
def isSupportedTerminal() -> bool:
    return isSupportedVSCodeTerminal() or isSupportedJetBrainsTerminal() or bool(os.environ.get("FORCE_CODE_TERMINAL"))


def isProcessRunning(pid: int) -> bool:
    if pid <= 1:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def makeAncestorPidLookup():
    task: Optional[asyncio.Task[set[int]]] = None

    async def lookup() -> set[int]:
        nonlocal task
        if task is None:
            async def load() -> set[int]:
                return set(await getAncestorPidsAsync(os.getppid(), 10))
            task = asyncio.create_task(load())
        return await task

    return lookup


def isVSCodeIde(ide: Optional[IdeType]) -> bool:
    config = supportedIdeConfigs.get(ide or "")
    return bool(config and config.get("ideKind") == "vscode")


def isJetBrainsIde(ide: Optional[IdeType]) -> bool:
    config = supportedIdeConfigs.get(ide or "")
    return bool(config and config.get("ideKind") == "jetbrains")


def getTerminalIdeType() -> Optional[IdeType]:
    if not isSupportedTerminal():
        return None
    terminal = getattr(env, "terminal", None)
    return terminal if terminal in supportedIdeConfigs else None


async def getSortedIdeLockfiles() -> List[str]:
    lockfiles: List[tuple[str, float]] = []
    for lock_dir in await getIdeLockfilesPaths():
        try:
            for entry in os.scandir(lock_dir):
                if entry.name.endswith(".lock"):
                    lockfiles.append((entry.path, entry.stat().st_mtime))
        except OSError:
            continue
    lockfiles.sort(key=lambda item: item[1], reverse=True)
    return [path for path, _ in lockfiles]


async def readIdeLockfile(path: str) -> Optional[IdeLockfileInfo]:
    try:
        content = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        log_error("Failed to read IDE lockfile", error)
        return None

    try:
        parsed: LockfileJsonContent = json.loads(content)
    except Exception:
        parsed = {"workspaceFolders": [line.strip() for line in content.splitlines() if line.strip()]}

    filename = os.path.basename(path)
    if not filename.endswith(".lock"):
        return None
    try:
        port = int(filename[:-5])
    except ValueError:
        return None

    return {
        "workspaceFolders": list(parsed.get("workspaceFolders") or []),
        "port": port,
        "pid": parsed.get("pid"),
        "ideName": parsed.get("ideName"),
        "useWebSocket": parsed.get("transport") == "ws",
        "runningInWindows": parsed.get("runningInWindows") is True,
        "authToken": parsed.get("authToken"),
    }


async def checkIdeConnection(host: str, port: int, timeout___500: int = 500) -> bool:
    try:
        connection = asyncio.open_connection(host, port)
        _, writer = await asyncio.wait_for(connection, timeout=timeout___500 / 1000)
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


async def getIdeLockfilesPaths() -> List[str]:
    paths = [os.path.join(get_vivian_config_home_dir(), "ide")]
    if get_platform() != "wsl":
        return paths
    users_dir = Path("/mnt/c/Users")
    if users_dir.exists():
        try:
            for child in users_dir.iterdir():
                if child.name not in {"Public", "Default", "Default User", "All Users"}:
                    paths.append(str(child / ".vivian" / "ide"))
        except OSError:
            pass
    return paths


async def cleanupStaleIdeLockfiles() -> None:
    for lockfile_path in await getSortedIdeLockfiles():
        lockfile = await readIdeLockfile(lockfile_path)
        should_delete = lockfile is None
        if lockfile is not None:
            pid = lockfile.get("pid")
            if pid:
                if not isProcessRunning(int(pid)):
                    should_delete = get_platform() != "wsl" or not await checkIdeConnection("127.0.0.1", int(lockfile["port"]))
            else:
                should_delete = not await checkIdeConnection("127.0.0.1", int(lockfile["port"]))
        if should_delete:
            try:
                os.unlink(lockfile_path)
            except OSError as error:
                log_error("Failed to delete stale IDE lockfile", error)


async def maybeInstallIDEExtension(ideType: IdeType) -> Optional[IDEExtensionInstallationStatus]:
    try:
        installed_version = await installIDEExtension(ideType)
        return {"installed": True, "error": None, "installedVersion": installed_version, "ideType": ideType}
    except Exception as error:
        log_error("IDE extension install failed", error)
        return {"installed": False, "error": str(error), "installedVersion": None, "ideType": ideType}


async def findAvailableIDE() -> Optional[DetectedIDEInfo]:
    global _current_ide_search_generation
    _current_ide_search_generation += 1
    generation = _current_ide_search_generation
    await cleanupStaleIdeLockfiles()
    loop = asyncio.get_running_loop()
    start = loop.time()
    while loop.time() - start < 30:
        if generation != _current_ide_search_generation:
            return None
        if getIsScrollDraining():
            await asyncio.sleep(1)
            continue
        ides = await detectIDEs(False)
        if generation != _current_ide_search_generation:
            return None
        if len(ides) == 1:
            return ides[0]
        await asyncio.sleep(1)
    return None


async def detectIDEs(includeInvalid: bool) -> List[DetectedIDEInfo]:
    detected: List[DetectedIDEInfo] = []
    env_port_raw = os.environ.get("vivian_CODE_SSE_PORT")
    env_port = int(env_port_raw) if env_port_raw and env_port_raw.isdigit() else None
    cwd = os.path.normpath(getOriginalCwd())
    lockfile_infos = await asyncio.gather(*(readIdeLockfile(path) for path in await getSortedIdeLockfiles()))
    get_ancestors = makeAncestorPidLookup()
    needs_ancestry_check = get_platform() != "wsl" and isSupportedTerminal()

    for lockfile in lockfile_infos:
        if not lockfile:
            continue
        if is_env_truthy(os.environ.get("vivian_CODE_IDE_SKIP_VALID_CHECK")):
            is_valid = True
        elif env_port is not None and lockfile["port"] == env_port:
            is_valid = True
        else:
            is_valid = False
            for ide_path in lockfile.get("workspaceFolders", []):
                if not ide_path:
                    continue
                resolved = os.path.normpath(os.path.abspath(ide_path))
                if get_platform() == "windows":
                    is_valid = cwd.lower() == resolved.lower() or cwd.lower().startswith(resolved.lower() + os.sep)
                else:
                    is_valid = cwd == resolved or cwd.startswith(resolved + os.sep)
                if is_valid:
                    break
        if not is_valid and not includeInvalid:
            continue
        if needs_ancestry_check and not (env_port is not None and lockfile["port"] == env_port):
            pid = lockfile.get("pid")
            if not pid or not isProcessRunning(int(pid)):
                continue
            if os.getppid() != int(pid):
                ancestors = await get_ancestors()
                if int(pid) not in ancestors:
                    continue
        ide_name = lockfile.get("ideName") or (toIDEDisplayName(getattr(envDynamic, "terminal", None)) if isSupportedTerminal() else "IDE")
        detected.append({
            "url": f"ws://127.0.0.1:{lockfile['port']}" if lockfile.get("useWebSocket") else f"http://127.0.0.1:{lockfile['port']}/sse",
            "name": ide_name,
            "workspaceFolders": lockfile.get("workspaceFolders", []),
            "port": lockfile["port"],
            "isValid": is_valid,
            "authToken": lockfile.get("authToken"),
            "ideRunningInWindows": lockfile.get("runningInWindows"),
        })
    if not includeInvalid and env_port is not None:
        env_match = [ide for ide in detected if ide["isValid"] and ide["port"] == env_port]
        if len(env_match) == 1:
            return env_match
    return detected


async def maybeNotifyIDEConnected(client):
    notifier = getattr(client, "notification", None)
    if callable(notifier):
        await notifier({"method": "ide_connected", "params": {"pid": os.getpid()}})


def hasAccessToIDEExtensionDiffFeature(mcpClients):
    return any(getattr(client, "type", None) == "connected" and getattr(client, "name", None) == "ide" for client in (mcpClients or []))


async def isIDEExtensionInstalled(ideType: IdeType) -> bool:
    if isVSCodeIde(ideType):
        command = await getVSCodeIDECommand(ideType)
        if not command:
            return False
        result = await exec_file_no_throw(command, ["--list-extensions"], env=getInstallationEnv())
        return EXTENSION_ID in (result.get("stdout") or "")
    if isJetBrainsIde(ideType):
        return await isJetBrainsPluginInstalledCached(ideType)
    return False


async def installIDEExtension(ideType: IdeType) -> Optional[str]:
    if not isVSCodeIde(ideType):
        return None
    command = await getVSCodeIDECommand(ideType)
    if not command:
        return None
    version = await getInstalledVSCodeExtensionVersion(command)
    if version:
        return version
    await asyncio.sleep(0.5)
    result = await exec_file_no_throw(command, ["--force", "--install-extension", EXTENSION_ID], env=getInstallationEnv())
    if result.get("code") != 0:
        raise RuntimeError(f"{result.get('code')}: {result.get('stderr') or result.get('error')}")
    return getvivianCodeVersion()


def getInstallationEnv() -> Optional[dict[str, str]]:
    if get_platform() == "linux":
        return {**os.environ, "DISPLAY": ""}
    return None


def getvivianCodeVersion() -> str:
    return os.environ.get("vivian_CODE_VERSION") or os.environ.get("VIVIAN_VERSION") or "0.0.0"


async def getInstalledVSCodeExtensionVersion(command: str) -> Optional[str]:
    result = await exec_file_no_throw(command, ["--list-extensions", "--show-versions"], env=getInstallationEnv())
    for line in (result.get("stdout") or "").splitlines():
        extension_id, _, version = line.partition("@")
        if extension_id == EXTENSION_ID and version:
            return version
    return None


def getVSCodeIDECommandByParentProcess() -> Optional[str]:
    if get_platform() != "macos":
        return None
    pid = os.getppid()
    app_names = {
        "Visual Studio Code.app": "code",
        "Cursor.app": "cursor",
        "Windsurf.app": "windsurf",
        "Visual Studio Code - Insiders.app": "code",
        "VSCodium.app": "codium",
    }
    suffix = "/Contents/MacOS/Electron"
    for _ in range(10):
        if not pid or pid in {0, 1}:
            break
        command = getProcessCommand(pid)
        if command:
            for app_name, executable in app_names.items():
                marker = app_name + suffix
                app_index = command.find(marker)
                if app_index != -1:
                    folder_end = app_index + len(app_name)
                    return command[:folder_end] + f"/Contents/Resources/app/bin/{executable}"
        ppid_raw = exec_file_no_throw_sync("ps", ["-o", "ppid=", "-p", str(pid)], timeout=1).get("stdout", "").strip()
        if not ppid_raw:
            break
        try:
            pid = int(ppid_raw)
        except ValueError:
            break
    return None


async def getVSCodeIDECommand(ideType: IdeType) -> Optional[str]:
    parent_executable = getVSCodeIDECommandByParentProcess()
    if parent_executable and os.path.exists(parent_executable):
        return parent_executable
    ext = ".cmd" if get_platform() == "windows" else ""
    if ideType == "vscode":
        return "code" + ext
    if ideType == "cursor":
        return "cursor" + ext
    if ideType == "windsurf":
        return "windsurf" + ext
    return None


async def isCursorInstalled() -> bool:
    return (await exec_file_no_throw("cursor", ["--version"])).get("code") == 0


async def isWindsurfInstalled() -> bool:
    return (await exec_file_no_throw("windsurf", ["--version"])).get("code") == 0


async def isVSCodeInstalled() -> bool:
    result = await exec_file_no_throw("code", ["--help"])
    return result.get("code") == 0 and "Visual Studio Code" in (result.get("stdout") or "")


async def detectRunningIDEsImpl() -> List[IdeType]:
    platform_name = get_platform()
    if platform_name == "macos":
        cmd = 'ps aux | grep -E "Visual Studio Code|Code Helper|Cursor Helper|Windsurf Helper|IntelliJ IDEA|PyCharm|WebStorm|PhpStorm|RubyMine|CLion|GoLand|Rider|DataGrip|AppCode|DataSpell|Aqua|Gateway|Fleet|Android Studio" | grep -v grep'
        result = await exec_file_no_throw("sh", ["-c", cmd])
    elif platform_name == "windows":
        cmd = 'tasklist | findstr /I "Code.exe Cursor.exe Windsurf.exe idea64.exe pycharm64.exe webstorm64.exe phpstorm64.exe rubymine64.exe clion64.exe goland64.exe rider64.exe datagrip64.exe appcode.exe dataspell64.exe aqua64.exe gateway64.exe fleet.exe studio64.exe"'
        result = await exec_file_no_throw("cmd", ["/c", cmd])
    else:
        cmd = 'ps aux | grep -E "code|cursor|windsurf|idea|pycharm|webstorm|phpstorm|rubymine|clion|goland|rider|datagrip|dataspell|aqua|gateway|fleet|android-studio" | grep -v grep'
        result = await exec_file_no_throw("sh", ["-c", cmd])
    normalized = (result.get("stdout") or "").lower()
    running: List[IdeType] = []
    for ide, config in supportedIdeConfigs.items():
        keywords = config["processKeywordsMac"] if platform_name == "macos" else config["processKeywordsWindows"] if platform_name == "windows" else config["processKeywordsLinux"]
        for keyword in keywords:
            if keyword.lower() in normalized:
                if ide == "vscode" and platform_name == "linux" and ("cursor" in normalized or "appcode" in normalized):
                    continue
                running.append(ide)
                break
    return running


async def detectRunningIDEs() -> List[IdeType]:
    global _cached_running_ides
    _cached_running_ides = await detectRunningIDEsImpl()
    return list(_cached_running_ides)


async def detectRunningIDEsCached() -> List[IdeType]:
    if _cached_running_ides is None:
        return await detectRunningIDEs()
    return list(_cached_running_ides)


def resetDetectRunningIDEs() -> None:
    global _cached_running_ides
    _cached_running_ides = None
    isSupportedVSCodeTerminal.cache_clear()
    isSupportedJetBrainsTerminal.cache_clear()
    isSupportedTerminal.cache_clear()


def getConnectedIdeName(mcpClients):
    ideClient = next((client for client in (mcpClients or []) if getattr(client, "type", None) == "connected" and getattr(client, "name", None) == "ide"), None)
    return getIdeClientName(ideClient)


def getIdeClientName(ideClient=None):
    return getattr(ideClient, "displayName", None) or getattr(ideClient, "name", None)


_EDITOR_DISPLAY_NAMES = {
    "code": "VS Code",
    "cursor": "Cursor",
    "windsurf": "Windsurf",
    "antigravity": "Antigravity",
    "vi": "Vim",
    "vim": "Vim",
    "nano": "nano",
    "notepad": "Notepad",
    "start /wait notepad": "Notepad",
    "emacs": "Emacs",
    "subl": "Sublime Text",
    "atom": "Atom",
}


def toIDEDisplayName(terminal):
    if not terminal:
        return "IDE"
    config = supportedIdeConfigs.get(terminal)
    if config:
        return config.get("displayName", terminal)
    editor_name = _EDITOR_DISPLAY_NAMES.get(str(terminal).lower().strip())
    if editor_name:
        return editor_name
    command = str(terminal).split(" ")[0] if terminal else ""
    command_name = os.path.basename(command).lower() if command else None
    if command_name:
        mapped = _EDITOR_DISPLAY_NAMES.get(command_name)
        if mapped:
            return mapped
        return command_name.capitalize()
    return str(terminal).capitalize() if terminal else "IDE"


def getConnectedIdeClient(mcpClients=None):
    return next((client for client in (mcpClients or []) if getattr(client, "type", None) == "connected" and getattr(client, "name", None) == "ide"), None)


async def closeOpenDiffs(ideClient):
    notifier = getattr(ideClient, "notification", None)
    if callable(notifier):
        await notifier({"method": "close_open_diffs", "params": {}})


async def initializeIdeIntegration(onIdeDetected=None):
    running = await detectRunningIDEsCached()
    if callable(onIdeDetected):
        maybe_coro = onIdeDetected(running)
        if asyncio.iscoroutine(maybe_coro):
            await maybe_coro
    return running


async def installFromArtifactory(command):
    result = await exec_file_no_throw(command, ["--force", "--install-extension", EXTENSION_ID], env=getInstallationEnv())
    if result.get("code") != 0:
        raise RuntimeError(result.get("stderr") or result.get("error") or "install failed")
    return getvivianCodeVersion()


is_process_running = isProcessRunning
is_vscode_ide = isVSCodeIde
is_jetbrains_ide = isJetBrainsIde
get_terminal_ide_type = getTerminalIdeType
get_sorted_ide_lockfiles = getSortedIdeLockfiles
read_ide_lockfile = readIdeLockfile
check_ide_connection = checkIdeConnection
get_ide_lockfiles_paths = getIdeLockfilesPaths
cleanup_stale_ide_lockfiles = cleanupStaleIdeLockfiles
maybe_install_ide_extension = maybeInstallIDEExtension
find_available_ide = findAvailableIDE
detect_ides = detectIDEs
maybe_notify_ide_connected = maybeNotifyIDEConnected
has_access_to_ide_extension_diff_feature = hasAccessToIDEExtensionDiffFeature
is_ide_extension_installed = isIDEExtensionInstalled
install_ide_extension = installIDEExtension
get_installation_env = getInstallationEnv
get_vivian_code_version = getvivianCodeVersion
get_installed_vscode_extension_version = getInstalledVSCodeExtensionVersion
get_vscode_ide_command_by_parent_process = getVSCodeIDECommandByParentProcess
get_vscode_ide_command = getVSCodeIDECommand
is_cursor_installed = isCursorInstalled
is_windsurf_installed = isWindsurfInstalled
is_vscode_installed = isVSCodeInstalled
detect_running_ides_impl = detectRunningIDEsImpl
detect_running_ides = detectRunningIDEs
detect_running_ides_cached = detectRunningIDEsCached
reset_detect_running_ides = resetDetectRunningIDEs
get_connected_ide_name = getConnectedIdeName
get_ide_client_name = getIdeClientName
to_ide_display_name = toIDEDisplayName
get_connected_ide_client = getConnectedIdeClient
close_open_diffs = closeOpenDiffs
initialize_ide_integration = initializeIdeIntegration
install_from_artifactory = installFromArtifactory

