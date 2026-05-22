"""
Port of src/utils/bash/shellPrefix.ts
Shell prefix command formatting.
"""
from __future__ import annotations
import shlex
from .shellQuote import quote


def format_shell_prefix_command(prefix, command):
    """Format a shell prefix command with proper quoting.
    
    Examples:
      'bash' -> "'bash' 'cmd'"
      '/usr/bin/bash -c' -> "'/usr/bin/bash' -c 'cmd'"
    """
    space_before_dash = prefix.rfind(" -")
    if space_before_dash > 0:
        exec_path = prefix[:space_before_dash]
        args = prefix[space_before_dash + 1:]
        return f"{quote([exec_path])} {args} {quote([command])}"
    else:
        return f"{quote([prefix])} {quote([command])}"


formatShellPrefixCommand = format_shell_prefix_command
