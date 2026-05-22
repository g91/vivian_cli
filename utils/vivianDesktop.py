"""
    passpass of src/utils/vivianDesktop.ts
"""
from __future__ import annotations

import os
import re
import asyncio
from pathlib import Path

from .debug import log_error
from .errors import is_enoent
from .json import parse_json
from .platform import SUPPORTED_PLATFORMS, get_platform


async def getvivianDesktopConfigPath():
    platform_name = get_platform()
    if platform_name not in SUPPORTED_PLATFORMS:
        raise RuntimeError(
            f"Unsupported platform: {platform_name} - vivian Desktop integration only works on macOS and WSL."
        )

    if platform_name == "macos":
        return str(
            Path.home()
            / "Library"
            / "Application Support"
            / "vivian"
            / "vivian_desktop_config.json"
        )

    windows_home = os.environ.get("USERPROFILE")
    if windows_home:
        normalized = windows_home.replace("\\", "/")
        wsl_path = re.sub(r"^[A-Za-z]:", "", normalized)
        config_path = f"/mnt/c{wsl_path}/AppData/Roaming/vivian/vivian_desktop_config.json"
        if await asyncio.to_thread(os.path.exists, config_path):
            return config_path

    users_dir = "/mnt/c/Users"
    try:
        entries = await asyncio.to_thread(os.scandir, users_dir)
        with entries as iterator:
            for entry in iterator:
                if not entry.is_dir():
                    continue
                if entry.name in {"Public", "Default", "Default User", "All Users"}:
                    continue
                candidate = os.path.join(
                    users_dir,
                    entry.name,
                    "AppData",
                    "Roaming",
                    "vivian",
                    "vivian_desktop_config.json",
                )
                if await asyncio.to_thread(os.path.exists, candidate):
                    return candidate
    except Exception as error:
        log_error("Failed to scan Windows users for vivian Desktop config", error)

    raise RuntimeError(
        "Could not find vivian Desktop config file in Windows. Make sure vivian Desktop is installed on Windows."
    )


async def readvivianDesktopMcpServers():
    if get_platform() not in SUPPORTED_PLATFORMS:
        raise RuntimeError(
            "Unsupported platform - vivian Desktop integration only works on macOS and WSL."
        )
    try:
        config_path = await getvivianDesktopConfigPath()
        try:
            config_content = await asyncio.to_thread(Path(config_path).read_text, encoding="utf-8")
        except Exception as error:
            if is_enoent(error):
                return {}
            raise

        config = parse_json(config_content, default=None)
        if not isinstance(config, dict):
            return {}

        mcp_servers = config.get("mcpServers")
        if not isinstance(mcp_servers, dict):
            return {}

        servers = {}
        for name, server_config in mcp_servers.items():
            if not isinstance(name, str) or not isinstance(server_config, dict):
                continue
            # Conservative validity check until the full MCP schema port is in place.
            if isinstance(server_config.get("command"), str):
                servers[name] = server_config
        return servers
    except Exception as error:
        log_error("Failed to read vivian Desktop MCP servers", error)
        return {}


get_vivian_desktop_config_path = getvivianDesktopConfigPath
read_vivian_desktop_mcp_servers = readvivianDesktopMcpServers

