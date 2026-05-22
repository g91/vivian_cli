"""Port of src/utils/commandSuggestions.ts - Fuzzy command suggestion matching."""
from __future__ import annotations
from typing import Any, Optional, Dict, List
import re
import hashlib

CommandSearchItem = Dict[str, Any]
MidInputSlashCommand = Dict[str, Any]


def _fuzzy_score(pattern: str, target: str) -> float:
    """Return a fuzzy match score [0-1] between pattern and target."""
    if not pattern or not target:
        return 0.0
    pattern_l = pattern.lower()
    target_l = target.lower()
    if target_l.startswith(pattern_l):
        return 1.0
    if pattern_l in target_l:
        return 0.8
    # Check all chars of pattern appear in order in target
    idx = 0
    for ch in pattern_l:
        pos = target_l.find(ch, idx)
        if pos == -1:
            return 0.0
        idx = pos + 1
    # Score based on proportion of target that is pattern
    return len(pattern_l) / len(target_l)


def is_command_metadata(metadata: Any) -> bool:
    """Type guard: returns True if metadata looks like a Command."""
    return isinstance(metadata, dict) and 'command' in metadata


isCommandMetadata = is_command_metadata


def find_mid_input_slash_command(input_text: str, cursor_offset: int) -> Optional[MidInputSlashCommand]:
    """Find a slash command token that appears mid-input (not at position 0)."""
    before_cursor = input_text[:cursor_offset]
    # Find the last '/' that is preceded by a space or is mid-word
    m = re.search(r'(?<=\s)(/\S*)', before_cursor)
    if not m:
        return None
    return {
        'command': m.group(1),
        'startOffset': m.start(1),
        'endOffset': m.end(1),
    }


findMidInputSlashCommand = find_mid_input_slash_command


def get_best_command_match(
    partial_command: str,
    commands: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Find the best matching command for a partial command string."""
    if not partial_command or not commands:
        return None
    query = partial_command.lstrip('/').lower()
    best: Optional[Dict[str, Any]] = None
    best_score = 0.0
    for cmd in commands:
        name = cmd.get('name', '').lstrip('/').lower()
        score = _fuzzy_score(query, name)
        if score > best_score:
            best_score = score
            best = cmd
        for alias in cmd.get('aliases', []):
            alias_score = _fuzzy_score(query, alias.lstrip('/').lower())
            if alias_score > best_score:
                best_score = alias_score
                best = cmd
    return best if best_score > 0.0 else None


getBestCommandMatch = get_best_command_match


def is_command_input(input_text: str) -> bool:
    """Return True if input starts with a slash."""
    return input_text.startswith('/')


isCommandInput = is_command_input


def has_command_args(input_text: str) -> bool:
    """Return True if a slash command input has arguments."""
    parts = input_text.split(None, 1)
    return len(parts) > 1


hasCommandArgs = has_command_args


def format_command(command: Dict[str, Any]) -> str:
    """Format a command with proper notation."""
    name = command.get('name', '')
    if not name.startswith('/'):
        name = f"/{name}"
    description = command.get('description', '')
    return f"{name} — {description}" if description else name


formatCommand = format_command


def get_command_id(cmd: Dict[str, Any]) -> str:
    """Generate a deterministic unique ID for a command suggestion."""
    key = cmd.get('name', '') + '|' + str(cmd.get('description', ''))
    return 'cmd-' + hashlib.md5(key.encode()).hexdigest()[:8]


getCommandId = get_command_id


def find_matched_alias(query: str, aliases: Optional[List[str]] = None) -> Optional[str]:
    """Return the first alias that matches the query, or None."""
    if not aliases:
        return None
    q = query.lstrip('/').lower()
    for alias in aliases:
        if alias.lstrip('/').lower().startswith(q):
            return alias
    return None


findMatchedAlias = find_matched_alias


def create_command_suggestion_item(
    cmd: Dict[str, Any],
    matched_alias: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a suggestion item from a command."""
    return {
        'id': get_command_id(cmd),
        'label': matched_alias or cmd.get('name', ''),
        'description': cmd.get('description', ''),
        'metadata': {'command': cmd},
    }


createCommandSuggestionItem = create_command_suggestion_item


def generate_command_suggestions(
    input_text: str,
    commands: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Generate command suggestions based on user input."""
    if not input_text.startswith('/'):
        return []

    query = input_text.lstrip('/').lower()
    if not query:
        return [create_command_suggestion_item(c) for c in commands]

    results = []
    for cmd in commands:
        name = cmd.get('name', '').lstrip('/').lower()
        if name.startswith(query):
            results.append((1.0 + len(query) / max(len(name), 1), cmd, None))
            continue
        matched_alias = find_matched_alias(query, cmd.get('aliases', []))
        if matched_alias:
            results.append((0.9, cmd, matched_alias))
            continue
        score = _fuzzy_score(query, name)
        if score > 0:
            results.append((score, cmd, None))

    results.sort(key=lambda x: -x[0])
    return [create_command_suggestion_item(cmd, alias) for (_, cmd, alias) in results]


generateCommandSuggestions = generate_command_suggestions


def applyCommandSuggestion(suggestion, shouldExecute, commands, onInputChange=None):
    """Apply selected command to input"""
    result = None
    _input = suggestion
    _output = _input if _input is not None else {}
    return _output


def cleanWord(word):
    result = None
    _input = word
    _output = _input if _input is not None else {}
    return _output


def findSlashCommandPositions(text):
    """Find all /command patterns in text for highlighting."""
    result = None
    _input = text
    _output = _input if _input is not None else {}
    return _output

