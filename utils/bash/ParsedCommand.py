"""
Port of src/utils/bash/ParsedCommand.ts
Parsed command classes for bash command analysis.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from .commands import extract_output_redirections, split_command_with_operators
from .treeSitterAnalysis import analyze_command


class OutputRedirection:
    def __init__(self, target, operator):
        self.target = target
        self.operator = operator


class RegexParsedCommand_DEPRECATED:
    """Legacy regex/shell-quote path. Used when tree-sitter is unavailable."""

    def __init__(self, command):
        self.originalCommand = command

    def __str__(self):
        return self.originalCommand

    def get_pipe_segments(self):
        """Split command into pipe segments."""
        try:
            parts = split_command_with_operators(self.originalCommand)
            segments = []
            current = []
            for part in parts:
                if isinstance(part, str) and part == "|":
                    if current:
                        segments.append(" ".join(current))
                        current = []
                elif isinstance(part, dict) and part.get("op") == "|":
                    if current:
                        segments.append(" ".join(current))
                        current = []
                else:
                    if isinstance(part, str):
                        current.append(part)
            if current:
                segments.append(" ".join(current))
            return segments if segments else [self.originalCommand]
        except Exception:
            return [self.originalCommand]

    def without_output_redirections(self):
        """Return command without output redirections."""
        if ">" not in self.originalCommand:
            return self.originalCommand
        result = extract_output_redirections(self.originalCommand)
        if result["redirections"]:
            return result["commandWithoutRedirections"]
        return self.originalCommand

    def get_output_redirections(self):
        """Get output redirections as list of OutputRedirection objects."""
        result = extract_output_redirections(self.originalCommand)
        return result["redirections"]

    def get_tree_sitter_analysis(self):
        """Returns None — regex fallback does not use tree-sitter."""
        return None

    # CamelCase aliases
    getPipeSegments = get_pipe_segments
    withoutOutputRedirections = without_output_redirections
    getOutputRedirections = get_output_redirections
    getTreeSitterAnalysis = get_tree_sitter_analysis


class TreeSitterParsedCommand:
    """Tree-sitter backed parsed command. Falls back to regex if no root node."""

    def __init__(self, command, root_node=None, pipe_positions=None,
                 redirection_nodes=None, analysis=None):
        self.originalCommand = command
        self._root_node = root_node
        self._pipe_positions = pipe_positions or []
        self._redirection_nodes = redirection_nodes or []
        self._analysis = analysis

    def __str__(self):
        return self.originalCommand

    def get_pipe_segments(self):
        """Split on pipe positions from tree-sitter."""
        if not self._pipe_positions:
            return RegexParsedCommand_DEPRECATED(self.originalCommand).get_pipe_segments()
        segments = []
        prev = 0
        for pos in sorted(self._pipe_positions):
            segments.append(self.originalCommand[prev:pos].strip())
            prev = pos + 1
        segments.append(self.originalCommand[prev:].strip())
        return [s for s in segments if s]

    def without_output_redirections(self):
        if ">" not in self.originalCommand:
            return self.originalCommand
        result = extract_output_redirections(self.originalCommand)
        if result["redirections"]:
            return result["commandWithoutRedirections"]
        return self.originalCommand

    def get_output_redirections(self):
        result = extract_output_redirections(self.originalCommand)
        return result["redirections"]

    def get_tree_sitter_analysis(self):
        if self._analysis is None and self._root_node is not None:
            self._analysis = analyze_command(self.originalCommand, self._root_node)
        return self._analysis

    getPipeSegments = get_pipe_segments
    withoutOutputRedirections = without_output_redirections
    getOutputRedirections = get_output_redirections
    getTreeSitterAnalysis = get_tree_sitter_analysis


def buildParsedCommandFromRoot(command: str, root) -> "TreeSitterParsedCommand":
    """Build a TreeSitterParsedCommand from a pre-parsed AST root.
    Lets callers that already have the tree skip the redundant native.parse call.
    """
    from vivian_cli.utils.bash.treeSitterAnalysis import analyze_command
    analysis = analyze_command(root, command)
    return TreeSitterParsedCommand(command, root_node=root, analysis=analysis)


# Single-entry cache (matches TS size-1 cache)
_last_cmd: Optional[str] = None
_last_result = None


async def _do_parse(command: str):
    """Try tree-sitter parse, fall back to regex."""
    if not command:
        return None
    try:
        from vivian_cli.utils.bash.parser import parseCommand
        data = await parseCommand(command)
        if data:
            return buildParsedCommandFromRoot(command, data["rootNode"])
    except Exception:
        _parse_error = None
    return RegexParsedCommand_DEPRECATED(command)


class _ParsedCommandFactory:
    """Matches the TS ParsedCommand singleton with a parse() method."""

    async def parse(self, command: str):
        global _last_cmd, _last_result
        if command == _last_cmd and _last_result is not None:
            return await _last_result
        import asyncio
        _last_cmd = command
        _last_result = asyncio.ensure_future(_do_parse(command))
        return await _last_result


ParsedCommand = _ParsedCommandFactory()
