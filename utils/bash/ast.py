"""
Port of src/utils/bash/ast.ts
AST-based bash command security analysis.
Fail-closed: any unrecognized structure returns 'too-complex'.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from .bashParser import SHELL_KEYWORDS
from .parser import parse_command_raw, PARSE_ABORTED

CMDSUB_PLACEHOLDER = "__CMDSUB_OUTPUT__"
VAR_PLACEHOLDER = "__TRACKED_VAR__"

STRUCTURAL_TYPES = {"program", "list", "pipeline", "redirected_statement"}
SEPARATOR_TYPES = {"&&", "||", "|", ";", "&", "|&", "\n"}

# Allowlisted node types for simple command extraction
SIMPLE_CMD_ALLOWLIST = {
    "program", "list", "pipeline", "redirected_statement",
    "command", "command_name", "word", "raw_string", "string",
    "simple_expansion", "variable_assignment",
    "concatenation", "string_content", "expansion",
    "heredoc_redirect", "heredoc_body", "heredoc_start", "heredoc_end",
    "file_redirect", "fd_redirect",
    "&&", "||", "|", ";", "&", "\n",
}


def contains_any_placeholder(value):
    """Check if a value contains any placeholder string."""
    return CMDSUB_PLACEHOLDER in value or VAR_PLACEHOLDER in value


def parse_for_security(command):
    """
    Parse a bash command for security analysis.
    Returns one of:
      {'kind': 'simple', 'commands': [...]}
      {'kind': 'too-complex', 'reason': str}
      {'kind': 'parse-unavailable'}
    
    Each command in 'commands' is:
      {'argv': [...], 'envVars': [...], 'redirects': [...], 'text': str}
    """
    import asyncio

    async def _do_parse():
        root = await parse_command_raw(command)
        if root is None:
            return {"kind": "parse-unavailable"}
        if root is PARSE_ABORTED:
            return {"kind": "too-complex", "reason": "parse aborted"}

        commands = []
        result = _walk_node(root, command, commands)
        if result is not None:
            return result
        return {"kind": "simple", "commands": commands}

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _do_parse())
                return future.result(timeout=1.0)
        else:
            return loop.run_until_complete(_do_parse())
    except Exception as e:
        return {"kind": "too-complex", "reason": str(e)}


def _walk_node(node, source, commands):
    """Walk AST node, extracting simple commands. Returns error dict or None on success."""
    if node is None:
        return None

    node_type = node.get("type", "")

    if node_type in STRUCTURAL_TYPES:
        for child in node.get("children", []):
            if child:
                err = _walk_node(child, source, commands)
                if err:
                    return err
        return None

    if node_type in SEPARATOR_TYPES:
        return None

    if node_type == "command":
        cmd = _extract_simple_command(node, source)
        if cmd is None:
            return {"kind": "too-complex", "reason": "complex command structure", "nodeType": node_type}
        commands.append(cmd)
        return None

    if node_type == "redirected_statement":
        for child in node.get("children", []):
            if child and child.get("type") == "command":
                err = _walk_node(child, source, commands)
                if err:
                    return err
        return None

    # Any other node type = too complex
    return {"kind": "too-complex", "reason": f"unsupported node type: {node_type}", "nodeType": node_type}


def _extract_simple_command(node, source):
    """Extract a SimpleCommand from a 'command' AST node."""
    argv = []
    env_vars = []
    redirects = []
    var_scope = {}

    for child in node.get("children", []):
        if not child:
            continue
        t = child.get("type", "")
        text = child.get("text", "")

        if t == "variable_assignment":
            # Parse VAR=val
            eq_idx = text.find("=")
            if eq_idx > 0:
                name = text[:eq_idx]
                val = text[eq_idx + 1:]
                val_clean = _unquote(val)
                var_scope[name] = val_clean
                env_vars.append({"name": name, "value": val_clean})

        elif t == "command_name":
            word_val = _resolve_word(text, var_scope)
            if word_val is None:
                return None
            argv.append(word_val)

        elif t in ("word", "raw_string", "string", "concatenation"):
            word_val = _resolve_word(text, var_scope)
            if word_val is None:
                return None
            argv.append(word_val)

        elif t in ("file_redirect", "heredoc_redirect", "fd_redirect"):
            # Extract redirect info
            op = ">"
            target = ""
            for rc in child.get("children", []):
                if rc:
                    rt = rc.get("type", "")
                    if rt in (">", ">>", "<", "<<", ">&", ">|", "<&", "&>", "&>>", "<<<"):
                        op = rt
                    elif rt in ("word", "raw_string", "string"):
                        target = _unquote(rc.get("text", ""))
            redirects.append({"op": op, "target": target})

        elif t not in SIMPLE_CMD_ALLOWLIST and t not in SEPARATOR_TYPES:
            # Unknown node - fail closed
            return None

    if not argv and not env_vars:
        return None

    start = node.get("startIndex", 0)
    end = node.get("endIndex", len(source))
    return {
        "argv": argv,
        "envVars": env_vars,
        "redirects": redirects,
        "text": source[start:end] if start < len(source) else node.get("text", ""),
    }


def _resolve_word(text, var_scope):
    """Resolve a word token to its string value.
    Returns None if the word contains dynamic content we can't resolve safely.
    """
    # Single-quoted: literal
    if text.startswith("'") and text.endswith("'"):
        return text[1:-1]
    # Double-quoted: check for expansions
    if text.startswith('"') and text.endswith('"'):
        inner = text[1:-1]
        # Simple variable refs ok if they resolve
        inner = re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)", lambda m: var_scope.get(m.group(1), VAR_PLACEHOLDER), inner)
        if contains_any_placeholder(inner):
            return VAR_PLACEHOLDER  # not a pure literal
        return inner
    # Command substitution
    if "$(" in text or "`" in text:
        return CMDSUB_PLACEHOLDER
    # Simple variable expansion
    if text.startswith("$") and re.match(r"^\$[A-Za-z_][A-Za-z0-9_]*$", text):
        name = text[1:]
        val = var_scope.get(name, VAR_PLACEHOLDER)
        return val
    # Arithmetic
    if text.startswith("$(("):
        return CMDSUB_PLACEHOLDER
    # Process substitution
    if text.startswith("<(") or text.startswith(">("):
        return None  # too complex
    # Plain word
    return text


def _unquote(text):
    """Strip surrounding quotes from a string."""
    if len(text) >= 2:
        if (text[0] == "'" and text[-1] == "'") or (text[0] == '"' and text[-1] == '"'):
            return text[1:-1]
    return text


parseForSecurity = parse_for_security
