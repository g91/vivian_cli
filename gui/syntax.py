"""Basic regex-based syntax highlighting for common languages."""
from __future__ import annotations
import re
from typing import List, Tuple
from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Weight.Bold)
    if italic:
        f.setFontItalic(True)
    return f


# VS Code dark+ palette
COLORS = {
    "keyword": "#569cd6",
    "string": "#ce9178",
    "number": "#b5cea8",
    "comment": "#6a9955",
    "function": "#dcdcaa",
    "class": "#4ec9b0",
    "operator": "#d4d4d4",
    "decorator": "#dcdcaa",
}

PYTHON_KEYWORDS = (
    "and as assert async await break class continue def del elif else except finally "
    "for from global if import in is lambda nonlocal not or pass raise return try "
    "while with yield True False None self cls"
).split()

JS_KEYWORDS = (
    "break case catch class const continue debugger default delete do else export "
    "extends finally for function if import in instanceof let new of return super "
    "switch this throw try typeof var void while with yield async await true false null undefined"
).split()


def _rules_for(language: str) -> List[Tuple[QRegularExpression, QTextCharFormat]]:
    kw_fmt = _fmt(COLORS["keyword"])
    str_fmt = _fmt(COLORS["string"])
    num_fmt = _fmt(COLORS["number"])
    com_fmt = _fmt(COLORS["comment"], italic=True)
    fn_fmt = _fmt(COLORS["function"])
    cls_fmt = _fmt(COLORS["class"])
    dec_fmt = _fmt(COLORS["decorator"])

    rules: List[Tuple[QRegularExpression, QTextCharFormat]] = []

    if language == "python":
        for kw in PYTHON_KEYWORDS:
            rules.append((QRegularExpression(rf"\b{kw}\b"), kw_fmt))
        rules.append((QRegularExpression(r"@\w+"), dec_fmt))
        rules.append((QRegularExpression(r"\bdef\s+(\w+)"), fn_fmt))
        rules.append((QRegularExpression(r"\bclass\s+(\w+)"), cls_fmt))
        rules.append((QRegularExpression(r"#[^\n]*"), com_fmt))
    elif language in ("javascript", "typescript"):
        for kw in JS_KEYWORDS:
            rules.append((QRegularExpression(rf"\b{kw}\b"), kw_fmt))
        rules.append((QRegularExpression(r"//[^\n]*"), com_fmt))
        rules.append((QRegularExpression(r"\bfunction\s+(\w+)"), fn_fmt))
        rules.append((QRegularExpression(r"\bclass\s+(\w+)"), cls_fmt))
    elif language in ("c", "cpp", "java", "rust", "go"):
        c_kws = (
            "auto break case char class const continue default do double else enum "
            "extern float for goto if int long register return short signed sizeof "
            "static struct switch typedef union unsigned void volatile while bool "
            "true false null nullptr new delete this public private protected static "
            "virtual override final namespace template typename using fn let mut pub "
            "impl trait self Self match where async await"
        ).split()
        for kw in c_kws:
            rules.append((QRegularExpression(rf"\b{kw}\b"), kw_fmt))
        rules.append((QRegularExpression(r"//[^\n]*"), com_fmt))

    # Numbers + strings (single-line) common to all
    rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), num_fmt))
    rules.append((QRegularExpression(r'"([^"\\]|\\.)*"'), str_fmt))
    rules.append((QRegularExpression(r"'([^'\\]|\\.)*'"), str_fmt))
    return rules


_EXT_LANG = {
    ".py": "python",
    ".pyw": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
}


def language_for_path(path: str) -> str:
    import os
    ext = os.path.splitext(path)[1].lower()
    return _EXT_LANG.get(ext, "")


class CodeHighlighter(QSyntaxHighlighter):
    def __init__(self, document, language: str = ""):
        super().__init__(document)
        self.rules = _rules_for(language) if language else []
        self._block_comment_start = QRegularExpression(r"/\*")
        self._block_comment_end = QRegularExpression(r"\*/")
        self._py_triple_single = QRegularExpression(r"'''")
        self._py_triple_double = QRegularExpression(r'"""')
        self._com_fmt = _fmt(COLORS["comment"], italic=True)
        self._str_fmt = _fmt(COLORS["string"])
        self._language = language

    def set_language(self, language: str):
        self.rules = _rules_for(language) if language else []
        self._language = language
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        for regex, fmt in self.rules:
            it = regex.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)

        # Multi-line strings/comments
        if self._language == "python":
            self._scan_multiline(text, self._py_triple_double, self._str_fmt, 1)
            self._scan_multiline(text, self._py_triple_single, self._str_fmt, 2)
        elif self._language in ("javascript", "typescript", "c", "cpp", "java", "rust", "go"):
            self._scan_block_comment(text)

    def _scan_multiline(self, text: str, delim: QRegularExpression, fmt, state: int):
        prev = self.previousBlockState()
        start = 0
        if prev == state:
            end_match = delim.match(text)
            if not end_match.hasMatch():
                self.setFormat(0, len(text), fmt)
                self.setCurrentBlockState(state)
                return
            end = end_match.capturedStart() + end_match.capturedLength()
            self.setFormat(0, end, fmt)
            start = end
        it = delim.globalMatch(text, start)
        while it.hasNext():
            m1 = it.next()
            if not it.hasNext():
                self.setFormat(m1.capturedStart(), len(text) - m1.capturedStart(), fmt)
                self.setCurrentBlockState(state)
                return
            m2 = it.next()
            self.setFormat(m1.capturedStart(), m2.capturedStart() + m2.capturedLength() - m1.capturedStart(), fmt)

    def _scan_block_comment(self, text: str):
        start = 0
        if self.previousBlockState() != 1:
            m = self._block_comment_start.match(text)
            start = m.capturedStart() if m.hasMatch() else -1
        while start >= 0:
            end_match = self._block_comment_end.match(text, start)
            if not end_match.hasMatch():
                self.setFormat(start, len(text) - start, self._com_fmt)
                self.setCurrentBlockState(1)
                return
            length = end_match.capturedStart() + end_match.capturedLength() - start
            self.setFormat(start, length, self._com_fmt)
            nxt = self._block_comment_start.match(text, start + length)
            start = nxt.capturedStart() if nxt.hasMatch() else -1
