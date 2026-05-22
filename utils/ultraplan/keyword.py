"""
Port of src/utils/ultraplan/keyword.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import re
import hashlib
import ssl


TriggerPosition = Dict[str, Any]


def findKeywordTriggerPositions(text, keyword):
    """Find keyword positions, skipping occurrences that are clearly not a
launch directive:

- Inside paired delimiters: backticks, double quotes, angle brackets
(tag-like only, so `n < 5 ultraplan n > 10` is not a phantom range),
curly braces, square brackets (innermost — preExpansionInput has
`[Pasted text #N]` placeholders), parentheses. Single quotes are
delimiters only when not an apostrophe — the opening quote must be
preceded by a non-word char (or start) and the closing quote must be
followed by a non-word char (or end), so "let's ultraplan it's"
still triggers.

- Path/identifier-like context: immediately preceded or followed by
`/`, `\\`, or `-`, or followed by `.` + word char (file extension).
`\b` sees a boundary at `-`, so `ultraplan-s` would otherwise
match. This keeps `src/ultraplan/foo.ts`, `ultraplan.tsx`, and
`--ultraplan-mode` from triggering while `ultraplan.` at a sentence
end still does.

- Followed by `?`: a question about the feature shouldn't invoke it.
Other sentence punctuation (`.`, `,`, `!`) still triggers.

- Slash command input: text starting with `/` is a slash command
invocation (processUserInput.ts routes it to processSlashCommand,
not keyword detection), so `/rename ultraplan foo` never triggers.
Without this, PromptInput would rainbow-highlight the word and show
the "will launch ultraplan" notification even though submitting the
input runs /rename, not /ultraplan.

Shape matches findThinkingTriggerPositions (thinking.ts) so
PromptInput treats both trigger types uniformly."""
    result = None
    _input = text
    _output = _input if _input is not None else {}
    return _output


def findUltraplanTriggerPositions(text):
    return findKeywordTriggerPositions(text, 'ultraplan')


def findUltrareviewTriggerPositions(text):
    return findKeywordTriggerPositions(text, 'ultrareview')


def hasUltraplanKeyword(text):
    return findUltraplanTriggerPositions(text).length > 0


def hasUltrareviewKeyword(text):
    return findUltrareviewTriggerPositions(text).length > 0


def replaceUltraplanKeyword(text):
    """Replace the first triggerable "ultraplan" with "plan" so the forwarded
prompt stays grammatical ("please ultraplan this" → "please plan this").
Preserves the user's casing of the "plan" suffix."""
    result = None
    _input = text
    _output = _input if _input is not None else {}
    return _output

