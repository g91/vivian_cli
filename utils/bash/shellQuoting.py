"""
Port of src/utils/bash/shellQuoting.ts
Shell command quoting utilities.
"""
from __future__ import annotations
import re
import shlex
from .shellQuote import quote
from .heredoc import extract_heredocs

NUL_REDIRECT_REGEX = re.compile(r'(\d?&?>+\s*)[Nn][Uu][Ll](?=\s|$|[|&;)\n])')

_HEREDOC_RE = re.compile(r'''<<-?\s*(?:(['"]) ?(\w+)\1|\\?(\w+))''')
_SINGLE_QUOTE_MULTILINE = re.compile(r"'(?:[^'\\]|\\.)*\n(?:[^'\\]|\\.)*'")
_DOUBLE_QUOTE_MULTILINE = re.compile(r'"(?:[^"\\]|\\.)*\n(?:[^"\\]|\\.)*"')


def contains_heredoc(command):
    """Detect if a command contains a heredoc pattern."""
    if re.search(r'\d\s*<<\s*\d', command):
        return False
    if re.search(r'\[\[\s*\d+\s*<<\s*\d+\s*\]\]', command):
        return False
    if re.search(r'\$\(\(.*<<.*\)\)', command):
        return False
    return bool(re.search(r'''<<-?\s*(?:(['"]?)(\w+)\1|\\?(\w+))''', command))


def contains_multiline_string(command):
    """Detect if a command contains multiline strings in quotes."""
    return bool(_SINGLE_QUOTE_MULTILINE.search(command) or _DOUBLE_QUOTE_MULTILINE.search(command))


def quote_shell_command(command, add_stdin_redirect=True):
    """Quote a shell command appropriately, preserving heredocs and multiline strings."""
    if contains_heredoc(command) or contains_multiline_string(command):
        escaped = command.replace("'", "'\"'\"'")
        quoted = "'" + escaped + "'"
        if contains_heredoc(command):
            return quoted
        return (quoted + " < /dev/null") if add_stdin_redirect else quoted
    if add_stdin_redirect:
        return quote([command, "<", "/dev/null"])
    return quote([command])


def has_stdin_redirect(command):
    """Detect if a command already has a stdin redirect."""
    return bool(re.search(r'(?:^|[\s;&|])<(?![<(])\s*\S+', command))


def should_add_stdin_redirect(command):
    """Check if stdin redirect can be safely added to a command."""
    if contains_heredoc(command):
        return False
    if has_stdin_redirect(command):
        return False
    return True


def rewrite_windows_null_redirect(command):
    """Rewrite Windows CMD-style >nul redirects to POSIX /dev/null."""
    return NUL_REDIRECT_REGEX.sub(r'\g<1>/dev/null', command)


# CamelCase aliases matching TypeScript exports
containsHeredoc = contains_heredoc
containsMultilineString = contains_multiline_string
quoteShellCommand = quote_shell_command
hasStdinRedirect = has_stdin_redirect
shouldAddStdinRedirect = should_add_stdin_redirect
rewriteWindowsNullRedirect = rewrite_windows_null_redirect

