"""
Port of src/utils/terminalPanel.ts
"""
from __future__ import annotations

from typing import Optional
import os
import subprocess
import asyncio

from ..bootstrap.state import getSessionId
from .cleanupRegistry import register_cleanup
from .cwd import pwd
from .debug import logForDebugging


TMUX_SESSION = "panel"
_instance: Optional["TerminalPanel"] = None


class TerminalPanel:
    def __init__(self, hasTmux: Optional[bool] = None):
        self.hasTmux = hasTmux
        self.cleanupRegistered = False

    def toggle(self) -> None:
        self.showShell()

    def checkTmux(self) -> bool:
        if self.hasTmux is not None:
            return self.hasTmux
        result = subprocess.run(
            ["tmux", "-V"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.hasTmux = result.returncode == 0
        if not self.hasTmux:
            logForDebugging(
                "Terminal panel: tmux not found, falling back to non-persistent shell"
            )
        return self.hasTmux

    def hasSession(self) -> bool:
        result = subprocess.run(
            ["tmux", "-L", getTerminalPanelSocket(), "has-session", "-t", TMUX_SESSION],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

    def createSession(self) -> bool:
        shell = os.environ.get("SHELL") or "/bin/bash"
        cwd = pwd()
        socket = getTerminalPanelSocket()
        result = subprocess.run(
            [
                "tmux",
                "-L",
                socket,
                "new-session",
                "-d",
                "-s",
                TMUX_SESSION,
                "-c",
                cwd,
                shell,
                "-l",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logForDebugging(
                f"Terminal panel: failed to create tmux session: {result.stderr.strip()}"
            )
            return False

        subprocess.run(
            [
                "tmux",
                "-L",
                socket,
                "bind-key",
                "-n",
                "M-j",
                "detach-client",
                ";",
                "set-option",
                "-g",
                "status-style",
                "bg=default",
                ";",
                "set-option",
                "-g",
                "status-left",
                "",
                ";",
                "set-option",
                "-g",
                "status-right",
                " Alt+J to return to vivian ",
                ";",
                "set-option",
                "-g",
                "status-right-style",
                "fg=brightblack",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if not self.cleanupRegistered:
            self.cleanupRegistered = True

            async def cleanup() -> None:
                try:
                    process = subprocess.Popen(
                        ["tmux", "-L", socket, "kill-server"],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    process.poll()
                except Exception:
                    pass

            register_cleanup(cleanup)

        return True

    def attachSession(self) -> None:
        subprocess.run(
            ["tmux", "-L", getTerminalPanelSocket(), "attach-session", "-t", TMUX_SESSION],
            check=False,
        )

    def showShell(self) -> None:
        if self.checkTmux() and self.ensureSession():
            self.attachSession()
        else:
            self.runShellDirect()

    def ensureSession(self) -> bool:
        if self.hasSession():
            return True
        return self.createSession()

    def runShellDirect(self) -> None:
        shell = os.environ.get("SHELL") or "/bin/bash"
        subprocess.run(
            [shell, "-i", "-l"],
            cwd=pwd(),
            env=os.environ.copy(),
            check=False,
        )



def getTerminalPanelSocket():
    """Get the tmux socket name for the terminal panel.
Uses a unique socket per vivian Code instance (based on session ID)
so that each instance has its own isolated terminal panel."""
    sessionId = getSessionId()
    return f"vivian-panel-{sessionId[:8]}"


def getTerminalPanel():
    """Return the singleton TerminalPanel, creating it lazily on first use."""
    global _instance
    if _instance is None:
        _instance = TerminalPanel()
    return _instance


get_terminal_panel_socket = getTerminalPanelSocket
get_terminal_panel = getTerminalPanel

