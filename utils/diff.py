"""
    pass of src/utils/diff
"""
from __future__ import annotations

import difflib
from typing import Any, TypedDict

from ..bootstrap.state import addToTotalLinesChanged, getLocCounter
from ..services.analytics.index import logEvent
from .array import count


CONTEXT_LINES = 3
DIFF_TIMEOUT_MS = 5_000
AMPERSAND_TOKEN = "<<:AMPERSAND_TOKEN:>>"
DOLLAR_TOKEN = "<<:DOLLAR_TOKEN:>>"


class StructuredPatchHunk(TypedDict):
    oldStart: int
    oldLines: int
    newStart: int
    newLines: int
    lines: list[str]


def _convert_leading_tabs_to_spaces(content: str) -> str:
    return "\n".join(line.expandtabs(2) for line in content.splitlines())


def _normalize_for_whitespace(line: str, ignore_whitespace: bool) -> str:
    return " ".join(line.split()) if ignore_whitespace else line


def _build_hunks(
    old_content: str,
    new_content: str,
    *,
    ignore_whitespace: bool,
    context: int,
) -> list[StructuredPatchHunk]:
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    matcher = difflib.SequenceMatcher(
        None,
        [_normalize_for_whitespace(line, ignore_whitespace) for line in old_lines],
        [_normalize_for_whitespace(line, ignore_whitespace) for line in new_lines],
    )

    hunks: list[StructuredPatchHunk] = []
    for group in matcher.get_grouped_opcodes(context):
        if not group:
            continue
        first_tag, first_i1, _, first_j1, _ = group[0]
        old_start = first_i1 + 1 if first_tag != "insert" else first_i1
        new_start = first_j1 + 1 if first_tag != "delete" else first_j1
        hunk_lines: list[str] = []
        old_count = 0
        new_count = 0

        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                for line in old_lines[i1:i2]:
                    hunk_lines.append(f" {line}")
                old_count += i2 - i1
                new_count += j2 - j1
            elif tag == "delete":
                for line in old_lines[i1:i2]:
                    hunk_lines.append(f"-{line}")
                old_count += i2 - i1
            elif tag == "insert":
                for line in new_lines[j1:j2]:
                    hunk_lines.append(f"+{line}")
                new_count += j2 - j1
            elif tag == "replace":
                for line in old_lines[i1:i2]:
                    hunk_lines.append(f"-{line}")
                for line in new_lines[j1:j2]:
                    hunk_lines.append(f"+{line}")
                old_count += i2 - i1
                new_count += j2 - j1

        hunks.append(
            {
                "oldStart": old_start,
                "oldLines": old_count,
                "newStart": new_start,
                "newLines": new_count,
                "lines": hunk_lines,
            }
        )
    return hunks


def adjustHunkLineNumbers(hunks, offset):
    """Shifts hunk line numbers by offset. Use when getPatchForDisplay received"""
    if offset == 0:
        return hunks
    return [
        {
            **hunk,
            "oldStart": hunk["oldStart"] + offset,
            "newStart": hunk["newStart"] + offset,
        }
        for hunk in hunks
    ]


def escapeForDiff(s):
    return s.replace("&", AMPERSAND_TOKEN).replace("$", DOLLAR_TOKEN)


def unescapeFromDiff(s):
    return s.replace(AMPERSAND_TOKEN, "&").replace(DOLLAR_TOKEN, "$")


def countLinesChanged(patch, newFileContent=None):
    """Count lines added and removed in a patch and update the total"""
    if len(patch) == 0 and newFileContent is not None:
        num_additions = len(newFileContent.splitlines()) or 1
        num_removals = 0
    else:
        num_additions = sum(count(hunk["lines"], lambda line: line.startswith("+")) for hunk in patch)
        num_removals = sum(count(hunk["lines"], lambda line: line.startswith("-")) for hunk in patch)

    addToTotalLinesChanged(num_additions, num_removals)

    loc_counter = getLocCounter()
    if loc_counter is not None:
        loc_counter.add(num_additions, {"type": "added"})
        loc_counter.add(num_removals, {"type": "removed"})

    logEvent(
        "tengu_file_changed",
        {"lines_added": num_additions, "lines_removed": num_removals},
    )


def getPatchFromContents(__filePath__oldContent__newContent__ignoreWhitespace___false__singleHunk___false___=None):
    options = __filePath__oldContent__newContent__ignoreWhitespace___false__singleHunk___false___ or {}
    old_content = escapeForDiff(options.get("oldContent", ""))
    new_content = escapeForDiff(options.get("newContent", ""))
    hunks = _build_hunks(
        old_content,
        new_content,
        ignore_whitespace=bool(options.get("ignoreWhitespace", False)),
        context=100_000 if options.get("singleHunk", False) else CONTEXT_LINES,
    )
    return [
        {**hunk, "lines": [unescapeFromDiff(line) for line in hunk["lines"]]}
        for hunk in hunks
    ]


def getPatchForDisplay(__filePath__fileContents__edits__ignoreWhitespace___false___=None):
    """Get a patch for display with edits applied"""
    options = __filePath__fileContents__edits__ignoreWhitespace___false___ or {}
    prepared_file_contents = escapeForDiff(
        _convert_leading_tabs_to_spaces(options.get("fileContents", ""))
    )
    new_content = prepared_file_contents
    for edit in options.get("edits", []):
        if isinstance(edit, dict):
            old_string = edit.get("old_string") or edit.get("oldString") or ""
            new_string = edit.get("new_string") or edit.get("newString") or ""
            replace_all = bool(edit.get("replace_all", False))
        else:
            old_string = getattr(edit, "old_string", getattr(edit, "oldString", ""))
            new_string = getattr(edit, "new_string", getattr(edit, "newString", ""))
            replace_all = bool(getattr(edit, "replace_all", False))
        escaped_old = escapeForDiff(_convert_leading_tabs_to_spaces(old_string))
        escaped_new = escapeForDiff(_convert_leading_tabs_to_spaces(new_string))
        if replace_all:
            new_content = new_content.replace(escaped_old, escaped_new)
        else:
            new_content = new_content.replace(escaped_old, escaped_new, 1)

    hunks = _build_hunks(
        prepared_file_contents,
        new_content,
        ignore_whitespace=bool(options.get("ignoreWhitespace", False)),
        context=CONTEXT_LINES,
    )
    return [
        {**hunk, "lines": [unescapeFromDiff(line) for line in hunk["lines"]]}
        for hunk in hunks
    ]


adjust_hunk_line_numbers = adjustHunkLineNumbers
escape_for_diff = escapeForDiff
unescape_from_diff = unescapeFromDiff
count_lines_changed = countLinesChanged
get_patch_from_contents = getPatchFromContents
get_patch_for_display = getPatchForDisplay

