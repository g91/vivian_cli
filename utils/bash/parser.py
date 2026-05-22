"""
Port of src/utils/bash/parser.ts
Async wrapper around the bash parser for command analysis.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from .bashParser import parse_source, SHELL_KEYWORDS

Node = Dict[str, Any]

# Sentinel for "parser attempted but aborted"
PARSE_ABORTED = object()


async def ensure_initialized():
    """No-op: pure-Python parser requires no init."""
    return None


async def parse_command(command):
    """Parse a bash command, returning {rootNode, envVars, commandNode, originalCommand}."""
    root = parse_source(command)
    if root is None:
        return None
    env_vars = _extract_env_vars_from_root(root)
    command_node = _find_command_node(root)
    return {
        "rootNode": root,
        "envVars": env_vars,
        "commandNode": command_node,
        "originalCommand": command,
    }


async def parse_command_raw(command):
    """Raw parse - skips findCommandNode/extractEnvVars."""
    root = parse_source(command)
    return root


def _find_command_node(root):
    """Find the first 'command' node in the tree."""
    if not root:
        return None
    if root.get("type") == "command":
        return root
    for child in root.get("children", []):
        if child:
            result = _find_command_node(child)
            if result:
                return result
    return None


def _extract_env_vars_from_root(root):
    """Extract leading VAR=val assignments from the parse tree."""
    env_vars = []
    for child in root.get("children", []):
        if not child:
            continue
        if child.get("type") == "variable_assignment":
            env_vars.append(child.get("text", ""))
        elif child.get("type") == "command":
            # Check children of command for var assignments before command name
            for grandchild in child.get("children", []):
                if not grandchild:
                    continue
                if grandchild.get("type") == "variable_assignment":
                    env_vars.append(grandchild.get("text", ""))
                elif grandchild.get("type") == "command_name":
                    break
            break
    return env_vars


def find_command_node(node, parent=None):
    """Find the command node in the tree."""
    return _find_command_node(node)


def extract_env_vars(command_node):
    """Extract env var assignments from a command node."""
    env_vars = []
    if command_node:
        for child in command_node.get("children", []):
            if child and child.get("type") == "variable_assignment":
                env_vars.append(child.get("text", ""))
    return env_vars


def extract_command_arguments(command_node):
    """Extract argv from a command node (argv[0] = command name)."""
    if not command_node:
        return []
    args = []
    for child in command_node.get("children", []):
        if not child:
            continue
        t = child.get("type", "")
        if t == "variable_assignment":
            continue
        text = child.get("text", "")
        if t == "raw_string":
            # Strip quotes
            text = text[1:-1] if text.startswith("'") and text.endswith("'") else text
        elif t == "string":
            text = text[1:-1] if text.startswith('"') and text.endswith('"') else text
        if text:
            args.append(text)
    return args


parseCommand = parse_command
parseCommandRaw = parse_command_raw
ensureInitialized = ensure_initialized
findCommandNode = find_command_node
extractEnvVars = extract_env_vars
extractCommandArguments = extract_command_arguments
