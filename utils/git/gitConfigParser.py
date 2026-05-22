"""Git config file parser — mirrors src/utils/git/gitConfigParser.ts"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


def parse_git_config_value(
    git_dir: str,
    section: str,
    subsection: Optional[str],
    key: str,
) -> Optional[str]:
    """Read a single value from a .git/config file."""
    try:
        config = (Path(git_dir) / "config").read_text(encoding="utf-8")
        return parse_config_string(config, section, subsection, key)
    except OSError:
        return None


def parse_config_string(
    config: str,
    section: str,
    subsection: Optional[str],
    key: str,
) -> Optional[str]:
    """Parse a git config string and return the first matching value."""
    section_lower = section.lower()
    key_lower = key.lower()
    in_section = False

    for line in config.split("\n"):
        trimmed = line.strip()
        if not trimmed or trimmed[0] in ("#", ";"):
            continue
        if trimmed[0] == "[":
            in_section = _matches_section_header(trimmed, section_lower, subsection)
            continue
        if not in_section:
            continue
        parsed = _parse_key_value(trimmed)
        if parsed and parsed[0].lower() == key_lower:
            return parsed[1]
    return None


def _matches_section_header(
    line: str,
    section_lower: str,
    subsection: Optional[str],
) -> bool:
    """Return True if the given '[...]' header matches section+subsection."""
    m = re.match(r'^\[([a-zA-Z0-9-]+)(?:\s+"((?:[^"\\]|\\.)*)"|)\]$', line)
    if not m:
        return False
    hdr_section = m.group(1).lower()
    hdr_subsection = m.group(2)
    if hdr_section != section_lower:
        return False
    if subsection is None:
        return hdr_subsection is None
    # Subsection comparison is case-sensitive; handle backslash escapes
    if hdr_subsection is None:
        return False
    decoded = hdr_subsection.replace("\\\\", "\x00").replace('\\"', '"').replace("\x00", "\\")
    return decoded == subsection


def _parse_key_value(line: str) -> Optional[tuple[str, str]]:
    """Parse a ``key = value`` line. Returns (key, value) or None."""
    eq_pos = line.find("=")
    if eq_pos < 0:
        return None
    key = line[:eq_pos].strip()
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9-]*$", key):
        return None
    raw_value = line[eq_pos + 1:]
    value = _parse_value(raw_value)
    return (key, value)


def _parse_value(raw: str) -> str:
    """Unescape a git config value (handles inline comments and quoting)."""
    value = ""
    raw = raw.strip()
    in_quote = False
    i = 0
    while i < len(raw):
        ch = raw[i]
        if in_quote:
            if ch == '"':
                in_quote = False
            elif ch == "\\":
                i += 1
                if i < len(raw):
                    esc = raw[i]
                    if esc == "n":
                        value += "\n"
                    elif esc == "t":
                        value += "\t"
                    elif esc == "\\":
                        value += "\\"
                    elif esc == '"':
                        value += '"'
                    else:
                        value += esc
            else:
                value += ch
        else:
            if ch == '"':
                in_quote = True
            elif ch in ("#", ";"):
                break
            elif ch == "\\":
                i += 1
                if i < len(raw):
                    value += raw[i]
            else:
                value += ch
        i += 1
    return value.strip()
