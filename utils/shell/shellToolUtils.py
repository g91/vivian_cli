"""Port of src/utils/shell/shellToolUtils.ts."""
from __future__ import annotations

import os

from ...tools.BashTool.toolName import BASH_TOOL_NAME
from ...tools.PowerShellTool.toolName import POWERSHELL_TOOL_NAME
from ..envUtils import is_env_defined_falsy, is_env_truthy
from ..platform import get_platform


SHELL_TOOL_NAMES: list[str] = [BASH_TOOL_NAME, POWERSHELL_TOOL_NAME]


def isPowerShellToolEnabled() -> bool:
    """Runtime gate for PowerShellTool."""
    if get_platform() != "windows":
        return False
    if os.environ.get("USER_TYPE") == "ant":
        return not is_env_defined_falsy(os.environ.get("vivian_CODE_USE_POWERSHELL_TOOL"))
    return is_env_truthy(os.environ.get("vivian_CODE_USE_POWERSHELL_TOOL"))

