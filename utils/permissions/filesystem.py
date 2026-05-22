"""Port of src/utils/permissions/filesystem.ts"""
from __future__ import annotations
import os
import fnmatch
from pathlib import Path
from typing import Optional, List, Tuple, Any, Dict
from functools import lru_cache


DANGEROUS_FILES = (
    '.gitconfig', '.gitmodules',
    '.bashrc', '.bash_profile',
    '.zshrc', '.zprofile', '.profile',
    '.ripgreprc', '.mcp.json', '.vivian.json',
)

DANGEROUS_DIRECTORIES = (
    '.git', '.vscode', '.idea', '.vivian',
)


def normalizeCaseForComparison(path: str) -> str:
    """Normalize a path to lowercase for case-insensitive security comparisons."""
    return path.lower()


def getvivianTempDir() -> str:
    """Get or create a temporary directory for vivian operations."""
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), 'vivian-code')
    os.makedirs(tmp, exist_ok=True)
    return tmp


def relativePath(from_path: str, to_path: str) -> str:
    """Return a POSIX-style relative path from from_path to to_path."""
    try:
        return os.path.relpath(to_path, from_path).replace(os.sep, '/')
    except ValueError:
        return to_path.replace(os.sep, '/')


def toPosixPath(path: str) -> str:
    """Convert a path to POSIX format for pattern matching."""
    return path.replace(os.sep, '/')


def getvivianSkillScope(file_path: str) -> Optional[Dict[str, str]]:
    """Check if a file is inside a .vivian/skills/{name}/ directory; return scope info."""
    abs_path = os.path.abspath(os.path.expanduser(file_path))
    abs_lower = abs_path.lower()
    cwd = os.getcwd()
    home = os.path.expanduser('~')
    bases = [
        (os.path.join(cwd, '.vivian', 'skills'), '/.vivian/skills/'),
        (os.path.join(home, '.vivian', 'skills'), '~/.vivian/skills/'),
    ]
    for base_dir, prefix in bases:
        base_lower = base_dir.lower()
        if abs_lower.startswith(base_lower + os.sep.lower()):
            rest = abs_path[len(base_dir) + 1:]
            rest_posix = rest.replace(os.sep, '/')
            slash = rest_posix.find('/')
            if slash <= 0:
                return None
            skill_name = rest_posix[:slash]
            if not skill_name or skill_name == '.' or '..' in skill_name:
                return None
            if any(c in skill_name for c in '*?[]'):
                return None
            return {'skillName': skill_name, 'pattern': prefix + skill_name + '/**'}
    return None


def pathInWorkingPath(path: str, working_path: str) -> bool:
    """Return True if path is inside or equal to working_path."""
    path = os.path.normpath(path)
    working_path = os.path.normpath(working_path)
    return path == working_path or path.startswith(working_path + os.sep)


def pathInAllowedWorkingPath(path: str, working_paths: List[str]) -> bool:
    """Return True if path is inside any of the allowed working paths."""
    return any(pathInWorkingPath(path, wp) for wp in working_paths)


def isvivianSettingsPath(file_path: str) -> bool:
    """Return True if the file path is a vivian settings file that should be protected."""
    abs_path = os.path.abspath(os.path.expanduser(file_path))
    lower = normalizeCaseForComparison(abs_path)
    return lower.endswith('.vivian/settings.json') or lower.endswith('.vivian/settings.local.json')


def checkPathSafetyForAutoEdit(file_path: str) -> bool:
    """Return True if the file path is safe for auto-editing (not a dangerous file)."""
    basename = os.path.basename(file_path).lower()
    if basename in (f.lower() for f in DANGEROUS_FILES):
        return False
    parts = file_path.replace(os.sep, '/').split('/')
    for part in parts:
        if part.lower() in (d.lower() for d in DANGEROUS_DIRECTORIES):
            return False
    return True


def checkEditableInternalPath(file_path: str, working_paths: List[str]) -> bool:
    """Return True if the path is in the working directory and safe for editing."""
    abs_path = os.path.abspath(os.path.expanduser(file_path))
    if not pathInAllowedWorkingPath(abs_path, working_paths):
        return False
    return checkPathSafetyForAutoEdit(abs_path)


def checkReadableInternalPath(file_path: str, working_paths: List[str]) -> bool:
    """Return True if the path is in the working directory (readable)."""
    abs_path = os.path.abspath(os.path.expanduser(file_path))
    return pathInAllowedWorkingPath(abs_path, working_paths)


def matchingRuleForInput(
    file_path: str,
    rules: List[Dict[str, Any]],
    behavior: str,
    working_paths: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Find the first matching permission rule for a file path."""
    abs_path = os.path.abspath(os.path.expanduser(file_path))
    posix_path = abs_path.replace(os.sep, '/')
    for rule in rules:
        if rule.get('ruleBehavior') != behavior:
            continue
        rule_value = rule.get('ruleValue', {})
        rule_content = rule_value.get('ruleContent')
        if rule_content is None:
            # Tool-wide rule - matches all
            return rule
        # Try glob matching
        if fnmatch.fnmatch(posix_path, rule_content) or fnmatch.fnmatch(abs_path, rule_content):
            return rule
        # Try path-based matching
        if abs_path == rule_content or posix_path == rule_content:
            return rule
    return None
