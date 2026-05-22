"""Port of src/utils/env.ts."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List
import os
import asyncio
import platform
import sys
from functools import lru_cache

from .envUtils import get_vivian_config_home_dir, is_env_truthy
from .findExecutable import find_executable
from .which import which


Platform = str


JETBRAINS_IDES = [
    "pycharm",
    "intellij",
    "webstorm",
    "phpstorm",
    "rubymine",
    "clion",
    "goland",
    "rider",
    "datagrip",
    "appcode",
    "dataspell",
    "aqua",
    "gateway",
    "fleet",
    "jetbrains",
    "androidstudio",
]


@lru_cache(maxsize=1)
def getGlobalvivianFile() -> str:
    legacy = os.path.join(get_vivian_config_home_dir(), ".config.json")
    if os.path.exists(legacy):
        return legacy
    filename = ".vivian.json"
    return os.path.join(os.environ.get("vivian_CONFIG_DIR") or os.path.expanduser("~"), filename)


async def isCommandAvailable(command):
    try:
        return bool(await which(command))
    except Exception:
        return False


def isConductor():
    """Checks if we're running via Conductor"""
    return os.environ.get("__CFBundleIdentifier") == 'com.conductor.app'


def detectTerminal():
    if os.environ.get("CURSOR_TRACE_ID"):
        return "cursor"
    askpass = (os.environ.get("VSCODE_GIT_ASKPASS_MAIN") or "").lower()
    if "cursor" in askpass:
        return "cursor"
    if "windsurf" in askpass:
        return "windsurf"
    if "antigravity" in askpass:
        return "antigravity"

    bundle_id = (os.environ.get("__CFBundleIdentifier") or "").lower()
    if "vscodium" in bundle_id:
        return "codium"
    if "windsurf" in bundle_id:
        return "windsurf"
    if "com.google.android.studio" in bundle_id:
        return "androidstudio"
    if bundle_id:
        for ide in JETBRAINS_IDES:
            if ide in bundle_id:
                return ide

    if os.environ.get("VisualStudioVersion"):
        return "visualstudio"

    if os.environ.get("TERMINAL_EMULATOR") == "JetBrains-JediTerm":
        return "pycharm"

    term = os.environ.get("TERM") or ""
    if term == "xterm-ghostty":
        return "ghostty"
    if "kitty" in term:
        return "kitty"

    if os.environ.get("TERM_PROGRAM"):
        return os.environ["TERM_PROGRAM"]
    if os.environ.get("TMUX"):
        return "tmux"
    if os.environ.get("STY"):
        return "screen"

    if os.environ.get("KONSOLE_VERSION"):
        return "konsole"
    if os.environ.get("GNOME_TERMINAL_SERVICE"):
        return "gnome-terminal"
    if os.environ.get("XTERM_VERSION"):
        return "xterm"
    if os.environ.get("VTE_VERSION"):
        return "vte-based"
    if os.environ.get("TERMINATOR_UUID"):
        return "terminator"
    if os.environ.get("KITTY_WINDOW_ID"):
        return "kitty"
    if os.environ.get("ALACRITTY_LOG"):
        return "alacritty"
    if os.environ.get("TILIX_ID"):
        return "tilix"

    if os.environ.get("WT_SESSION"):
        return "windows-terminal"
    if os.environ.get("SESSIONNAME") and term == "cygwin":
        return "cygwin"
    if os.environ.get("MSYSTEM"):
        return os.environ["MSYSTEM"].lower()
    if os.environ.get("ConEmuANSI") or os.environ.get("ConEmuPID") or os.environ.get("ConEmuTask"):
        return "conemu"

    if os.environ.get("WSL_DISTRO_NAME"):
        return f"wsl-{os.environ['WSL_DISTRO_NAME']}"
    if isSSHSession():
        return "ssh-session"

    if term:
        if "alacritty" in term:
            return "alacritty"
        if "rxvt" in term:
            return "rxvt"
        if "termite" in term:
            return "termite"
        return term

    if not sys.stdout.isatty():
        return "non-interactive"
    return None


def isSSHSession():
    return bool(
        os.environ.get("SSH_CONNECTION")
        or os.environ.get("SSH_CLIENT")
        or os.environ.get("SSH_TTY")
    )


@lru_cache(maxsize=1)
def detectDeploymentEnvironment():
    if is_env_truthy(os.environ.get("CODESPACES")):
        return "codespaces"
    if os.environ.get("GITPOD_WORKSPACE_ID"):
        return "gitpod"
    if os.environ.get("REPL_ID") or os.environ.get("REPL_SLUG"):
        return "replit"
    if os.environ.get("PROJECT_DOMAIN"):
        return "glitch"

    if is_env_truthy(os.environ.get("VERCEL")):
        return "vercel"
    if os.environ.get("RAILWAY_ENVIRONMENT_NAME") or os.environ.get("RAILWAY_SERVICE_NAME"):
        return "railway"
    if is_env_truthy(os.environ.get("RENDER")):
        return "render"
    if is_env_truthy(os.environ.get("NETLIFY")):
        return "netlify"
    if os.environ.get("DYNO"):
        return "heroku"
    if os.environ.get("FLY_APP_NAME") or os.environ.get("FLY_MACHINE_ID"):
        return "fly.io"
    if is_env_truthy(os.environ.get("CF_PAGES")):
        return "cloudflare-pages"
    if os.environ.get("DENO_DEPLOYMENT_ID"):
        return "deno-deploy"
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return "aws-lambda"
    if os.environ.get("AWS_EXECUTION_ENV") == "AWS_ECS_FARGATE":
        return "aws-fargate"
    if os.environ.get("AWS_EXECUTION_ENV") == "AWS_ECS_EC2":
        return "aws-ecs"
    if os.environ.get("K_SERVICE"):
        return "gcp-cloud-run"
    if os.environ.get("GOOGLE_CLOUD_PROJECT"):
        return "gcp"
    if os.environ.get("WEBSITE_SITE_NAME") or os.environ.get("WEBSITE_SKU"):
        return "azure-app-service"
    if os.environ.get("AZURE_FUNCTIONS_ENVIRONMENT"):
        return "azure-functions"
    if (os.environ.get("APP_URL") or "").find("ondigitalocean.app") != -1:
        return "digitalocean-app-platform"
    if os.environ.get("SPACE_CREATOR_USER_ID"):
        return "huggingface-spaces"

    if is_env_truthy(os.environ.get("GITHUB_ACTIONS")):
        return "github-actions"
    if is_env_truthy(os.environ.get("GITLAB_CI")):
        return "gitlab-ci"
    if os.environ.get("CIRCLECI"):
        return "circleci"
    if os.environ.get("BUILDKITE"):
        return "buildkite"
    if is_env_truthy(os.environ.get("CI")):
        return "ci"

    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        return "kubernetes"
    if os.path.exists("/.dockerenv"):
        return "docker"

    if env.platform == "darwin":
        return "unknown-darwin"
    if env.platform == "linux":
        return "unknown-linux"
    return "unknown-win32"


@lru_cache(maxsize=1)
async def _detect_package_managers() -> List[str]:
    package_managers: List[str] = []
    if await isCommandAvailable("npm"):
        package_managers.append("npm")
    if await isCommandAvailable("yarn"):
        package_managers.append("yarn")
    if await isCommandAvailable("pnpm"):
        package_managers.append("pnpm")
    return package_managers


@lru_cache(maxsize=1)
async def _detect_runtimes() -> List[str]:
    runtimes: List[str] = []
    if await isCommandAvailable("bun"):
        runtimes.append("bun")
    if await isCommandAvailable("deno"):
        runtimes.append("deno")
    if await isCommandAvailable("node"):
        runtimes.append("node")
    return runtimes


@lru_cache(maxsize=1)
def _is_wsl_environment() -> bool:
    try:
        return os.path.exists("/proc/sys/fs/binfmt_misc/WSLInterop")
    except Exception:
        return False


@lru_cache(maxsize=1)
def _is_npm_from_windows_path() -> bool:
    if not _is_wsl_environment():
        return False
    try:
        resolved = find_executable("npm", []).get("cmd", "")
        return str(resolved).startswith("/mnt/c/")
    except Exception:
        return False


async def _has_internet_access() -> bool:
    try:
        import urllib.request

        with urllib.request.urlopen("http://1.1.1.1", timeout=1):
            return True
    except Exception:
        return False


_platform = "win32" if sys.platform == "win32" else "darwin" if sys.platform == "darwin" else "linux"
env = SimpleNamespace(
    hasInternetAccess=_has_internet_access,
    isCI=is_env_truthy(os.environ.get("CI")),
    platform=_platform,
    arch=platform.machine().lower(),
    nodeVersion=os.environ.get("NODE_VERSION") or "python",
    terminal=detectTerminal(),
    isSSH=isSSHSession,
    getPackageManagers=_detect_package_managers,
    getRuntimes=_detect_runtimes,
    isRunningWithBun=lambda: False,
    isWslEnvironment=_is_wsl_environment,
    isNpmFromWindowsPath=_is_npm_from_windows_path,
    isConductor=isConductor,
    detectDeploymentEnvironment=detectDeploymentEnvironment,
)


def getHostPlatformForAnalytics():
    """Returns the host platform for analytics reporting."""
    override = os.environ.get("vivian_CODE_HOST_PLATFORM")
    if override == 'win32' or override == 'darwin' or override == 'linux':
        return override
    return env.platform

