"""Port of src/utils/textHighlighting.ts."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import re


TextHighlight = Dict[str, Any]
TextSegment = Dict[str, Any]
_ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*\x07|\][^\x1b]*\x1b\\)")


def _tokenize(text: str) -> List[Tuple[str, str]]:
    tokens: List[Tuple[str, str]] = []
    pos = 0
    for match in _ANSI_RE.finditer(text):
        if match.start() > pos:
            tokens.append(("text", text[pos:match.start()]))
        tokens.append(("ansi", match.group()))
        pos = match.end()
    if pos < len(text):
        tokens.append(("text", text[pos:]))
    return tokens


def _undo_ansi_codes(codes: List[str]) -> List[str]:
    if not codes:
        return []
    return ["\x1b[0m"]


class HighlightSegmenter:
    def __init__(self, text: str):
        self.text = text
        self.tokens = _tokenize(text)
        self.visible_pos = 0
        self.string_pos = 0
        self.token_idx = 0
        self.char_idx = 0
        self.codes: List[str] = []

    def segment(self, highlights: List[TextHighlight]) -> List[TextSegment]:
        segments: List[TextSegment] = []

        for highlight in highlights:
            before = self.segment_to(highlight["start"])
            if before:
                segments.append(before)

            highlighted = self.segment_to(highlight["end"])
            if highlighted:
                highlighted["highlight"] = highlight
                segments.append(highlighted)

        after = self.segment_to(float("inf"))
        if after:
            segments.append(after)
        return segments

    def segment_to(self, target_visible_pos: float) -> Optional[TextSegment]:
        if self.token_idx >= len(self.tokens) or target_visible_pos <= self.visible_pos:
            return None

        visible_start = self.visible_pos

        while self.token_idx < len(self.tokens):
            token_type, token_value = self.tokens[self.token_idx]
            if token_type != "ansi":
                break
            self.codes.append(token_value)
            self.string_pos += len(token_value)
            self.token_idx += 1

        string_start = self.string_pos
        codes_start = list(self.codes)

        while self.visible_pos < target_visible_pos and self.token_idx < len(self.tokens):
            token_type, token_value = self.tokens[self.token_idx]
            if token_type == "ansi":
                self.codes.append(token_value)
                self.string_pos += len(token_value)
                self.token_idx += 1
                continue

            chars_needed = target_visible_pos - self.visible_pos
            chars_available = len(token_value) - self.char_idx
            chars_to_take = min(int(chars_needed), chars_available) if target_visible_pos != float("inf") else chars_available

            self.string_pos += chars_to_take
            self.visible_pos += chars_to_take
            self.char_idx += chars_to_take

            if self.char_idx >= len(token_value):
                self.token_idx += 1
                self.char_idx = 0

        if self.string_pos == string_start:
            return None

        prefix_codes = reduceCodes(codes_start)
        suffix_codes = reduceCodes(self.codes)
        self.codes = list(suffix_codes)

        prefix = "".join(prefix_codes)
        suffix = "".join(_undo_ansi_codes(suffix_codes))

        return {
            "text": prefix + self.text[string_start:self.string_pos] + suffix,
            "start": visible_start,
        }



def segmentTextByHighlights(text, highlights):
    if len(highlights) == 0:
        return [{"text": text, "start": 0}]

    sorted_highlights = sorted(
        highlights,
        key=lambda h: (h["start"], -h["priority"]),
    )

    resolved_highlights: List[TextHighlight] = []
    used_ranges: List[Dict[str, int]] = []
    for highlight in sorted_highlights:
        if highlight["start"] == highlight["end"]:
            continue

        overlaps = any(
            (highlight["start"] >= range_["start"] and highlight["start"] < range_["end"])
            or (highlight["end"] > range_["start"] and highlight["end"] <= range_["end"])
            or (highlight["start"] <= range_["start"] and highlight["end"] >= range_["end"])
            for range_ in used_ranges
        )
        if not overlaps:
            resolved_highlights.append(highlight)
            used_ranges.append({"start": highlight["start"], "end": highlight["end"]})

    return HighlightSegmenter(text).segment(resolved_highlights)


def reduceCodes(codes):
    reduced: List[str] = []
    for code in codes:
        if code in ("\x1b[m", "\x1b[0m"):
            reduced.clear()
            continue
        if code.startswith("\x1b["):
            reduced.append(code)
    return reduced


segment_text_by_highlights = segmentTextByHighlights
reduce_codes = reduceCodes

