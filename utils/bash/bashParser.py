"""
Port of src/utils/bash/bashParser.ts
Pure-Python bash parser producing tree-sitter-bash-compatible ASTs.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional

TsNode = Dict[str, Any]

SHELL_KEYWORDS = {
    "if", "then", "elif", "else", "fi",
    "while", "until", "for", "in", "do", "done",
    "case", "esac", "function", "select",
}

DECL_KEYWORDS = {"export", "declare", "typeset", "readonly", "local"}
SPECIAL_VARS = {"?", "$", "@", "*", "#", "-", "!", "_"}

PARSE_TIMEOUT_MS = 50
MAX_NODES = 50_000

_node_count = [0]


def _make_node(node_type, text, start, end, children=None):
    _node_count[0] += 1
    return {
        "type": node_type,
        "text": text,
        "startIndex": start,
        "endIndex": end,
        "children": children or [],
        "childCount": len(children or []),
    }


def parse_source(source, timeout_ms=None):
    """Parse a bash source string into a tree-sitter-compatible AST."""
    _node_count[0] = 0
    try:
        return _parse_program(source)
    except Exception:
        return None


def _parse_program(src):
    """Parse a complete bash program into a 'program' node."""
    children = []
    stmts = _split_statements(src)
    pos = 0
    for stmt_text, stmt_start in stmts:
        stmt_text = stmt_text.strip()
        if not stmt_text:
            continue
        node = _parse_statement(stmt_text, stmt_start)
        if node:
            children.append(node)
    return _make_node("program", src, 0, len(src), children)


def _split_statements(src):
    """Split source into top-level statements, respecting quoting."""
    stmts = []
    current = []
    start = 0
    i = 0
    n = len(src)
    in_single = False
    in_double = False
    depth = 0

    while i < n:
        c = src[i]
        if in_single:
            if c == "'":
                in_single = False
            current.append(c)
            i += 1
            continue
        if in_double:
            if c == '"':
                in_double = False
            elif c == '\\' and i + 1 < n:
                current.append(c)
                current.append(src[i + 1])
                i += 2
                continue
            current.append(c)
            i += 1
            continue
        if c == "'":
            in_single = True
            current.append(c)
            i += 1
            continue
        if c == '"':
            in_double = True
            current.append(c)
            i += 1
            continue
        if c in ("(", "{"):
            depth += 1
            current.append(c)
            i += 1
            continue
        if c in (")", "}"):
            depth -= 1
            current.append(c)
            i += 1
            continue
        if depth == 0 and c in (";", "\n"):
            text = "".join(current).strip()
            if text:
                stmts.append((text, start))
            current = []
            start = i + 1
            i += 1
            continue
        current.append(c)
        i += 1

    text = "".join(current).strip()
    if text:
        stmts.append((text, start))
    return stmts


def _parse_statement(text, offset=0):
    """Parse a single statement."""
    stripped = text.strip()
    if not stripped:
        return None

    # Pipeline
    if _contains_pipeline(stripped):
        return _parse_pipeline(stripped, offset)

    # List (&&/||)
    for op in ("&&", "||"):
        if op in stripped and not _in_quotes(stripped, stripped.find(op)):
            return _parse_list(stripped, offset)

    # Simple command
    return _parse_command(stripped, offset)


def _contains_pipeline(text):
    """Check if text contains an unquoted pipe."""
    in_sq = in_dq = False
    for i, c in enumerate(text):
        if in_sq:
            if c == "'":
                in_sq = False
            continue
        if in_dq:
            if c == '"':
                in_dq = False
            continue
        if c == "'":
            in_sq = True
            continue
        if c == '"':
            in_dq = True
            continue
        if c == '|' and i + 1 < len(text) and text[i + 1] != '|':
            return True
    return False


def _in_quotes(text, pos):
    """Check if position is inside quotes."""
    in_sq = in_dq = False
    for i, c in enumerate(text):
        if i >= pos:
            return in_sq or in_dq
        if in_sq:
            if c == "'":
                in_sq = False
            continue
        if in_dq:
            if c == '"':
                in_dq = False
            continue
        if c == "'":
            in_sq = True
        elif c == '"':
            in_dq = True
    return False


def _parse_pipeline(text, offset=0):
    """Parse a pipeline: cmd1 | cmd2 | ..."""
    parts = _split_on_operator(text, "|")
    children = []
    pos = offset
    for part in parts:
        node = _parse_command(part.strip(), pos)
        if node:
            children.append(node)
        pos += len(part) + 1
    return _make_node("pipeline", text, offset, offset + len(text), children)


def _parse_list(text, offset=0):
    """Parse a list: cmd1 && cmd2 || cmd3"""
    children = []
    remaining = text
    pos = offset
    while remaining:
        for op in ("&&", "||"):
            idx = remaining.find(op)
            if idx != -1 and not _in_quotes(remaining, idx):
                left = remaining[:idx].strip()
                node = _parse_command(left, pos)
                if node:
                    children.append(node)
                children.append(_make_node(op, op, pos + idx, pos + idx + len(op)))
                remaining = remaining[idx + len(op):]
                pos += idx + len(op)
                break
        else:
            node = _parse_command(remaining.strip(), pos)
            if node:
                children.append(node)
            break
    return _make_node("list", text, offset, offset + len(text), children)


def _split_on_operator(text, op):
    """Split text on an unquoted operator."""
    parts = []
    current = []
    in_sq = in_dq = False
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if in_sq:
            if c == "'":
                in_sq = False
            current.append(c)
            i += 1
            continue
        if in_dq:
            if c == '"':
                in_dq = False
            current.append(c)
            i += 1
            continue
        if c == "'":
            in_sq = True
            current.append(c)
            i += 1
            continue
        if c == '"':
            in_dq = True
            current.append(c)
            i += 1
            continue
        if text[i:i+len(op)] == op:
            parts.append("".join(current))
            current = []
            i += len(op)
            continue
        current.append(c)
        i += 1
    parts.append("".join(current))
    return parts


def _parse_command(text, offset=0):
    """Parse a simple command into a 'command' node with argument children."""
    if not text.strip():
        return None

    # Check for env var assignments at start
    env_vars = []
    args = []
    tokens = _tokenize_command(text)

    for i, tok in enumerate(tokens):
        if i == 0 and re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', tok):
            env_vars.append(tok)
        elif re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', tok) and not args:
            env_vars.append(tok)
        else:
            args.append(tok)

    children = []
    pos = offset
    for ev in env_vars:
        children.append(_make_node("variable_assignment", ev, pos, pos + len(ev)))
        pos += len(ev) + 1

    if args:
        cmd_name = args[0]
        cmd_node = _make_node("command_name", cmd_name, pos, pos + len(cmd_name))
        arg_children = [cmd_node]
        pos += len(cmd_name) + 1
        for arg in args[1:]:
            arg_node = _parse_word(arg, pos)
            arg_children.append(arg_node)
            pos += len(arg) + 1
        children.extend(arg_children)

    return _make_node("command", text, offset, offset + len(text), children)


def _parse_word(text, offset=0):
    """Parse a word token."""
    if text.startswith("'") and text.endswith("'"):
        return _make_node("raw_string", text, offset, offset + len(text))
    if text.startswith('"') and text.endswith('"'):
        return _make_node("string", text, offset, offset + len(text))
    if text.startswith("$((") and text.endswith("))"):
        return _make_node("arithmetic_expansion", text, offset, offset + len(text))
    if text.startswith("$(") and text.endswith(")"):
        inner = text[2:-1]
        inner_node = _parse_command(inner, offset + 2)
        children = [inner_node] if inner_node else []
        return _make_node("command_substitution", text, offset, offset + len(text), children)
    if text.startswith("`") and text.endswith("`"):
        inner = text[1:-1]
        inner_node = _parse_command(inner, offset + 1)
        children = [inner_node] if inner_node else []
        return _make_node("command_substitution", text, offset, offset + len(text), children)
    if "$" in text:
        return _make_node("word", text, offset, offset + len(text))
    return _make_node("word", text, offset, offset + len(text))


def _tokenize_command(text):
    """Simple tokenizer for a single command (no operators)."""
    tokens = []
    current = []
    in_sq = in_dq = False
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if in_sq:
            current.append(c)
            if c == "'":
                in_sq = False
            i += 1
            continue
        if in_dq:
            current.append(c)
            if c == '"':
                in_dq = False
            elif c == '\\' and i + 1 < n:
                current.append(text[i + 1])
                i += 2
                continue
            i += 1
            continue
        if c == '\\' and i + 1 < n:
            current.append(text[i + 1])
            i += 2
            continue
        if c == "'":
            in_sq = True
            current.append(c)
            i += 1
            continue
        if c == '"':
            in_dq = True
            current.append(c)
            i += 1
            continue
        if c in (' ', '\t'):
            if current:
                tokens.append("".join(current))
                current = []
            i += 1
            continue
        current.append(c)
        i += 1
    if current:
        tokens.append("".join(current))
    return tokens


def ensure_parser_initialized():
    """No-op: pure-Python parser needs no async init."""
    return None


def get_parser_module():
    """Return a parser module dict with a parse function."""
    return {"parse": parse_source}


ensureParserInitialized = ensure_parser_initialized
getParserModule = get_parser_module
parseSource = parse_source
