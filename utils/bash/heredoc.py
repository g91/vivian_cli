"""
Port of src/utils/bash/heredoc.ts
Heredoc extraction and restoration utilities.
"""
from __future__ import annotations
import re
import secrets
from typing import Optional

HEREDOC_PLACEHOLDER_PREFIX = "__HEREDOC_"
HEREDOC_PLACEHOLDER_SUFFIX = "__"


def generate_placeholder_salt():
    """Generate a random hex string for placeholder uniqueness."""
    return secrets.token_hex(8)


def extract_heredocs(command, options=None):
    """Extract heredocs from a command string, replacing them with placeholders.
    Returns dict: {processedCommand: str, heredocs: dict}.
    """
    heredocs = {}
    if "<<" not in command:
        return {"processedCommand": command, "heredocs": heredocs}

    quoted_only = (options or {}).get("quotedOnly", False)
    salt = generate_placeholder_salt()
    result = command
    placeholder_idx = 0
    pos = 0

    while pos < len(result):
        idx = result.find("<<", pos)
        if idx == -1:
            break
        # Skip <<< (herestring)
        if idx + 2 < len(result) and result[idx + 2] == "<":
            pos = idx + 3
            continue
        # Skip digit<<digit (bitshift in arithmetic)
        if idx > 0 and result[idx - 1].isdigit():
            pos = idx + 2
            continue

        scan = idx + 2
        strip_tabs = False
        if scan < len(result) and result[scan] == "-":
            strip_tabs = True
            scan += 1

        # Skip spaces/tabs only
        while scan < len(result) and result[scan] in (" ", "\t"):
            scan += 1

        if scan >= len(result):
            pos = idx + 2
            continue

        quoted = False
        delimiter = ""
        delim_end = scan

        c = result[scan]
        if c in ("'", '"'):
            quote_char = c
            quoted = True
            delim_end = scan + 1
            while delim_end < len(result) and result[delim_end] != quote_char:
                delimiter += result[delim_end]
                delim_end += 1
            if delim_end < len(result):
                delim_end += 1  # skip closing quote
        elif c == "\\":
            # Backslash-escaped unquoted delimiter
            delim_end = scan + 1
            while delim_end < len(result) and (result[delim_end].isalnum() or result[delim_end] == "_"):
                delimiter += result[delim_end]
                delim_end += 1
        else:
            delim_end = scan
            while delim_end < len(result) and (result[delim_end].isalnum() or result[delim_end] == "_"):
                delimiter += result[delim_end]
                delim_end += 1

        if not delimiter:
            pos = idx + 2
            continue
        if quoted_only and not quoted:
            pos = idx + 2
            continue

        newline_pos = result.find("\n", delim_end)
        if newline_pos == -1:
            pos = idx + 2
            continue
        content_start = newline_pos + 1

        tab_pat = "\\t*" if strip_tabs else ""
        close_pat = "\n" + tab_pat + re.escape(delimiter) + "(\n|$)"
        close_match = re.search(close_pat, result[content_start:])
        if not close_match:
            pos = idx + 2
            continue

        content_end = content_start + close_match.end()
        placeholder = (
            HEREDOC_PLACEHOLDER_PREFIX
            + str(placeholder_idx)
            + "_"
            + salt
            + HEREDOC_PLACEHOLDER_SUFFIX
        )
        placeholder_idx += 1
        heredocs[placeholder] = {
            "fullText": result[idx:content_end],
            "delimiter": delimiter,
            "operatorStartIndex": idx,
            "operatorEndIndex": delim_end,
            "contentStartIndex": content_start,
            "contentEndIndex": content_end,
        }
        result = result[:idx] + placeholder + result[content_end:]
        pos = idx + len(placeholder)

    return {"processedCommand": result, "heredocs": heredocs}


def restore_heredocs_in_string(text, heredocs):
    """Replace placeholders with original heredoc text."""
    for placeholder, info in heredocs.items():
        text = text.replace(placeholder, info["fullText"])
    return text


def restore_heredocs(parts, heredocs, placeholder_map=None):
    """Restore heredoc placeholders in a list of command parts."""
    return [
        restore_heredocs_in_string(p, heredocs) if isinstance(p, str) else p
        for p in parts
    ]


# TypeScript-compatible aliases
extractHeredocs = extract_heredocs
restoreHeredocsInString = restore_heredocs_in_string
generatePlaceholderSalt = generate_placeholder_salt
