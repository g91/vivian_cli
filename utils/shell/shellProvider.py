"""Port of src/utils/shell/shellProvider.ts."""
from __future__ import annotations

from typing import Awaitable, Callable, Literal, Protocol, TypedDict


ShellType = Literal["bash", "powershell"]
SHELL_TYPES: tuple[ShellType, ...] = ("bash", "powershell")
DEFAULT_HOOK_SHELL: ShellType = "bash"


class BuildExecCommandResult(TypedDict):
	commandString: str
	cwdFilePath: str


class ShellProvider(Protocol):
	type: ShellType
	shellPath: str
	detached: bool

	def buildExecCommand(
		self,
		command: str,
		opts: dict,
	) -> Awaitable[BuildExecCommandResult]: ...

	def getSpawnArgs(self, commandString: str) -> list[str]: ...

	def getEnvironmentOverrides(self, command: str) -> Awaitable[dict[str, str]]: ...

