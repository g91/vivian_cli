"""
Port of src/utils/bash/treeSitterAnalysis.ts
Tree-sitter AST analysis utilities (Python fallback using regex-based analysis).
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple

TreeSitterNode = Dict[str, Any]
QuoteContext = Dict[str, Any]
CompoundStructure = Dict[str, Any]
DangerousPatterns = Dict[str, Any]
TreeSitterAnalysis = Dict[str, Any]


def collect_quote_spans(node, out, in_double):
    """Collect quote-related spans from the AST node tree."""
    t = node.get("type", "")
    if t == "raw_string":
        out["raw"].append((node.get("startIndex", 0), node.get("endIndex", 0)))
        return
    if t == "ansi_c_string":
        out["ansiC"].append((node.get("startIndex", 0), node.get("endIndex", 0)))
        return
    if t == "string":
        if not in_double:
            out["double"].append((node.get("startIndex", 0), node.get("endIndex", 0)))
        for child in node.get("children", []):
            if child:
                collect_quote_spans(child, out, True)
        return
    if t == "heredoc_redirect":
        is_quoted = False
        for child in node.get("children", []):
            if child and child.get("type") == "heredoc_start":
                first = (child.get("text") or "")[:1]
                is_quoted = first in ("'", '"', "\\")
                break
        if is_quoted:
            out["heredoc"].append((node.get("startIndex", 0), node.get("endIndex", 0)))
            return
    for child in node.get("children", []):
        if child:
            collect_quote_spans(child, out, in_double)


def build_position_set(spans):
    """Build a set of all character positions covered by the given spans."""
    positions = set()
    for start, end in spans:
        positions.update(range(start, end))
    return positions


def drop_contained_spans(spans):
    """Drop spans fully contained within another span, keeping only outermost."""
    if not spans:
        return spans
    sorted_spans = sorted(spans, key=lambda s: (s[0], -(s[1] - s[0])))
    result = []
    max_end = -1
    for start, end in sorted_spans:
        if start >= max_end:
            result.append((start, end))
            max_end = end
    return result


def remove_spans(command, spans):
    """Remove spans from a string."""
    if not spans:
        return command
    spans_sorted = sorted(drop_contained_spans(spans), key=lambda s: s[0], reverse=True)
    result = command
    for start, end in spans_sorted:
        result = result[:start] + result[end:]
    return result


def analyze_command_regex(command):
    """Perform regex-based analysis of a bash command (fallback without tree-sitter)."""
    # Remove single-quoted strings
    without_single = re.sub(r"'[^']*'", " ", command)
    # Remove double-quoted strings
    without_double = re.sub(r'"(?:[^"\\]|\\.)*"', " ", without_single)
    without_all = without_double

    quote_context = {
        "withDoubleQuotes": without_single,
        "fullyUnquoted": without_all,
        "unquotedKeepQuoteChars": re.sub(r"""'[^']*'|"(?:[^"\\]|\\.)*" """.strip(), " ", command),
    }

    has_compound = bool(re.search(r'&&|\|\||;', without_all))
    has_pipeline = bool(re.search(r'(?<![|])[|](?![|])', without_all))
    has_subshell = bool(re.search(r'\((?![^)]*\()', without_all))
    has_cmd_group = bool(re.search(r'\{[^}]+\}', without_all))

    operators = []
    for op in ["&&", "||", ";"]:
        if op in without_all:
            operators.append(op)

    segments = re.split(r'&&|\|\||;', without_all)
    segments = [s.strip() for s in segments if s.strip()]

    compound_structure = {
        "hasCompoundOperators": has_compound,
        "hasPipeline": has_pipeline,
        "hasSubshell": has_subshell,
        "hasCommandGroup": has_cmd_group,
        "operators": operators,
        "segments": segments,
    }

    # Dangerous patterns
    without_sq = re.sub(r"'[^']*'", " ", command)
    has_cmd_sub = bool(re.search(r'\$\([^)]*\)|`[^`]*`', without_sq))
    has_proc_sub = bool(re.search(r'[<>]\(', without_sq))
    has_param_exp = bool(re.search(r'\$\{[^}]*\}', without_sq))
    has_heredoc = "<<" in command
    has_comment = bool(re.search(r'(?:^|\s)#', without_sq))

    dangerous_patterns = {
        "hasCommandSubstitution": has_cmd_sub,
        "hasProcessSubstitution": has_proc_sub,
        "hasParameterExpansion": has_param_exp,
        "hasHeredoc": has_heredoc,
        "hasComment": has_comment,
    }

    return {
        "quoteContext": quote_context,
        "compoundStructure": compound_structure,
        "hasActualOperatorNodes": has_compound or has_pipeline,
        "dangerousPatterns": dangerous_patterns,
    }


def analyze_command(command, root_node=None):
    """Analyze a bash command for security-relevant structure."""
    if root_node is not None:
        out = {"raw": [], "ansiC": [], "double": [], "heredoc": []}
        collect_quote_spans(root_node, out, False)

        all_spans = out["raw"] + out["ansiC"] + out["double"] + out["heredoc"]
        without_all_quoted = remove_spans(command, all_spans)
        without_single = remove_spans(command, out["raw"] + out["ansiC"])

        quote_context = {
            "withDoubleQuotes": without_single,
            "fullyUnquoted": without_all_quoted,
            "unquotedKeepQuoteChars": without_all_quoted,
        }

        operators = []
        has_pipeline = False
        has_subshell = False
        has_cmd_group = False

        def walk(node):
            nonlocal has_pipeline, has_subshell, has_cmd_group
            t = node.get("type", "")
            if t in ("&&", "||", ";") and t not in operators:
                operators.append(t)
            if t == "pipeline":
                has_pipeline = True
            if t == "subshell":
                has_subshell = True
            if t == "command_group":
                has_cmd_group = True
            for child in node.get("children", []):
                if child:
                    walk(child)

        walk(root_node)

        compound_structure = {
            "hasCompoundOperators": len(operators) > 0,
            "hasPipeline": has_pipeline,
            "hasSubshell": has_subshell,
            "hasCommandGroup": has_cmd_group,
            "operators": operators,
            "segments": [],
        }

        cmd_sub = [False]
        proc_sub = [False]
        param_exp = [False]
        heredoc_found = [False]
        comment_found = [False]

        def walk2(node):
            t = node.get("type", "")
            if t in ("command_substitution", "backtick_command"):
                cmd_sub[0] = True
            if t == "process_substitution":
                proc_sub[0] = True
            if t in ("expansion", "simple_expansion"):
                param_exp[0] = True
            if t == "heredoc_redirect":
                heredoc_found[0] = True
            if t == "comment":
                comment_found[0] = True
            for child in node.get("children", []):
                if child:
                    walk2(child)

        walk2(root_node)

        dangerous_patterns = {
            "hasCommandSubstitution": cmd_sub[0],
            "hasProcessSubstitution": proc_sub[0],
            "hasParameterExpansion": param_exp[0],
            "hasHeredoc": heredoc_found[0],
            "hasComment": comment_found[0],
        }

        return {
            "quoteContext": quote_context,
            "compoundStructure": compound_structure,
            "hasActualOperatorNodes": len(operators) > 0 or has_pipeline,
            "dangerousPatterns": dangerous_patterns,
        }

    return analyze_command_regex(command)


# CamelCase aliases
analyzeCommand = analyze_command
collectQuoteSpans = collect_quote_spans
buildPositionSet = build_position_set
dropContainedSpans = drop_contained_spans
removeSpans = remove_spans

