"""Syntax-highlighted diff rendering — mirrors src/native-ts/color-diff/index.ts.

Renders unified-diff hunks (and whole files) with ANSI colour, syntax
highlighting via Pygments, and per-word diff colouring.  The public surface
matches the TypeScript NativeModule shape exactly:

    ColorDiff(hunk, firstLine, filePath, prefixContent?)
    ColorFile(code, filePath)
    getSyntaxTheme(themeName) -> SyntaxTheme
    getNativeModule() -> NativeModule | None
    __test  (dict of internal helpers, for unit tests)
"""
from __future__ import annotations

import os
import re
import difflib
from dataclasses import dataclass, field
from typing import Any, Optional, Union

# ─── ANSI constants ───────────────────────────────────────────────────────────

RESET = "\x1b[0m"
DIM   = "\x1b[2m"
UNDIM = "\x1b[22m"

# ─── Color types ─────────────────────────────────────────────────────────────

@dataclass
class RGBColor:
    r: int; g: int; b: int
    tag: str = "rgb"

@dataclass
class AnsiColor:
    index: int
    tag: str = "ansi"

@dataclass
class DefaultBgColor:
    tag: str = "default"

Color = Union[RGBColor, AnsiColor, DefaultBgColor]

def rgb(r: int, g: int, b: int) -> RGBColor:
    return RGBColor(r, g, b)

def ansiIdx(index: int) -> AnsiColor:
    return AnsiColor(index)

DEFAULT_BG = DefaultBgColor()

# ─── Color mode detection ────────────────────────────────────────────────────

def detectColorMode(theme: str) -> str:
    """Return 'truecolor', 'color256', or 'ansi' based on env."""
    if theme == "ansi":
        return "ansi"
    colorterm = os.environ.get("COLORTERM", "").lower()
    if colorterm in ("truecolor", "24bit"):
        return "truecolor"
    term = os.environ.get("TERM", "")
    if "256color" in term or colorterm == "256":
        return "color256"
    return "ansi"

def ansi256FromRgb(r: int, g: int, b: int) -> int:
    """Convert RGB to xterm-256 colour index."""
    if r == g == b:
        if r < 8:   return 16
        if r > 248: return 231
        return round((r - 8) / 247 * 24) + 232
    ri = round(r / 255 * 5)
    gi = round(g / 255 * 5)
    bi = round(b / 255 * 5)
    return 16 + 36 * ri + 6 * gi + bi

def colorToEscape(c: Color, fg: bool, mode: str) -> str:
    """Convert a Color to an ANSI escape sequence."""
    if isinstance(c, DefaultBgColor):
        return ""
    if mode == "truecolor":
        if isinstance(c, RGBColor):
            code = 38 if fg else 48
            return f"\x1b[{code};2;{c.r};{c.g};{c.b}m"
        idx = c.index
        code = 38 if fg else 48
        return f"\x1b[{code};5;{idx}m"
    if mode == "color256":
        if isinstance(c, RGBColor):
            idx = ansi256FromRgb(c.r, c.g, c.b)
        else:
            idx = c.index
        code = 38 if fg else 48
        return f"\x1b[{code};5;{idx}m"
    # ansi mode: map to basic 16 colours
    if isinstance(c, AnsiColor):
        if fg:
            return f"\x1b[{30 + c.index}m" if c.index < 8 else f"\x1b[{90 + c.index - 8}m"
        return f"\x1b[{40 + c.index}m" if c.index < 8 else f"\x1b[{100 + c.index - 8}m"
    # rgb → nearest ansi colour (very rough)
    return ""

# ─── Block / Highlight types ──────────────────────────────────────────────────

@dataclass
class Block:
    text: str
    fg: Optional[Color] = None
    bg: Optional[Color] = None
    bold: bool = False
    dim: bool = False

@dataclass
class HighlightLine:
    marker: str = " "        # '+', '-', or ' '
    lineNo: Optional[int] = None  # line number (1-based) for left gutter
    blocks: list[Block] = field(default_factory=list)

Highlight = list[HighlightLine]

def asTerminalEscaped(blocks: list[Block], mode: str, skipBackground: bool, dim: bool) -> str:
    """Render a list of Blocks to an ANSI string."""
    out = []
    for b in blocks:
        s = ""
        if b.fg:
            s += colorToEscape(b.fg, True, mode)
        if b.bg and not skipBackground:
            s += colorToEscape(b.bg, False, mode)
        if b.bold:
            s += "\x1b[1m"
        if b.dim or dim:
            s += DIM
        s += b.text
        if s != b.text:
            s += RESET
        out.append(s)
    return "".join(out)

# ─── Theme ────────────────────────────────────────────────────────────────────

@dataclass
class Theme:
    addLine: Color
    addWord: Color
    addDecoration: Color
    deleteLine: Color
    deleteWord: Color
    deleteDecoration: Color
    foreground: Optional[Color]
    background: Optional[Color]
    scopes: dict[str, Color] = field(default_factory=dict)

MONOKAI_SCOPES: dict[str, Color] = {
    "keyword":              rgb(249,  38, 114),
    "keyword.control":      rgb(249,  38, 114),
    "keyword.operator":     rgb(249,  38, 114),
    "storage":              rgb(249,  38, 114),
    "storage.type":         rgb(102, 217, 239),
    "entity.name.function": rgb(166, 226,  46),
    "entity.name.class":    rgb(166, 226,  46),
    "entity.name.type":     rgb(102, 217, 239),
    "string":               rgb(230, 219, 116),
    "string.regexp":        rgb(230, 219, 116),
    "constant":             rgb(174, 129, 255),
    "constant.numeric":     rgb(174, 129, 255),
    "constant.language":    rgb(249,  38, 114),
    "comment":              rgb(117, 113, 94),
    "punctuation":          rgb(248, 248, 242),
    "variable":             rgb(248, 248, 242),
    "support.function":     rgb(102, 217, 239),
    "support.class":        rgb(102, 217, 239),
    "meta.function-call":   rgb(102, 217, 239),
}

GITHUB_SCOPES: dict[str, Color] = {
    "keyword":              rgb( 87,  70, 175),
    "keyword.control":      rgb( 87,  70, 175),
    "storage":              rgb( 87,  70, 175),
    "storage.type":         rgb( 87,  70, 175),
    "entity.name.function": rgb(111,  66, 193),
    "entity.name.class":    rgb(111,  66, 193),
    "string":               rgb(  3,  47,  98),
    "string.regexp":        rgb( 3,  47,  98),
    "constant.numeric":     rgb(  0,  92,  35),
    "constant.language":    rgb(  0,  92,  35),
    "comment":              rgb(106, 115, 125),
    "variable":             rgb(  5,  80, 174),
}

ANSI_SCOPES: dict[str, Color] = {
    "keyword":          ansiIdx(5),
    "storage":          ansiIdx(5),
    "string":           ansiIdx(2),
    "constant.numeric": ansiIdx(1),
    "comment":          ansiIdx(8),
}

STORAGE_KEYWORDS = {
    "var", "let", "const", "function", "class", "return", "if", "else",
    "for", "while", "do", "switch", "case", "break", "continue", "import",
    "export", "from", "default", "new", "delete", "typeof", "instanceof",
    "in", "of", "try", "catch", "finally", "throw", "async", "await",
    "yield", "static", "extends", "super", "this", "null", "undefined",
    "true", "false", "void", "type", "interface", "enum", "namespace",
    "module", "declare", "abstract", "override", "readonly", "private",
    "protected", "public", "def", "class", "pass", "lambda", "with",
    "as", "assert", "del", "elif", "except", "global", "nonlocal", "raise",
    "not", "and", "or", "is", "None", "True", "False",
}

def defaultSyntaxThemeName(themeName: str) -> str:
    if themeName == "ansi":
        return "ansi"
    if not themeName or themeName.lower() in ("", "default"):
        return "Monokai Extended"
    return themeName

def buildTheme(themeName: str, mode: str) -> Theme:
    resolved = defaultSyntaxThemeName(themeName)
    if resolved == "ansi":
        scopes = ANSI_SCOPES
        add_line   = ansiIdx(2)   # green
        add_word   = ansiIdx(10)  # bright green
        del_line   = ansiIdx(1)   # red
        del_word   = ansiIdx(9)   # bright red
        add_dec    = ansiIdx(2)
        del_dec    = ansiIdx(1)
        fg         = ansiIdx(7)
        bg: Optional[Color] = None
    elif resolved == "GitHub":
        scopes   = GITHUB_SCOPES
        add_line = rgb(205, 255, 185)
        add_word = rgb(140, 235, 140)
        del_line = rgb(255, 195, 180)
        del_word = rgb(235, 130, 130)
        add_dec  = rgb(  0, 135,  51)
        del_dec  = rgb(164,  14,  14)
        fg       = rgb( 36,  41,  47)
        bg       = rgb(255, 255, 255)
    else:
        scopes   = MONOKAI_SCOPES
        add_line = rgb( 58,  78,  58)
        add_word = rgb( 80, 130,  80)
        del_line = rgb( 78,  47,  47)
        del_word = rgb(140,  70,  70)
        add_dec  = rgb(  0, 200,  80)
        del_dec  = rgb(220,  60,  60)
        fg       = rgb(248, 248, 242)
        bg       = rgb( 39,  40,  34)
    return Theme(
        addLine=add_line, addWord=add_word, addDecoration=add_dec,
        deleteLine=del_line, deleteWord=del_word, deleteDecoration=del_dec,
        foreground=fg, background=bg, scopes=scopes,
    )

# ─── Language detection ───────────────────────────────────────────────────────

FILENAME_LANGS: dict[str, str] = {
    "Makefile": "makefile", "Dockerfile": "docker",
    "Gemfile": "ruby", "Rakefile": "ruby",
    "CMakeLists.txt": "cmake",
}

EXT_LANGS: dict[str, str] = {
    ".py": "python", ".pyw": "python",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".jsx": "jsx", ".ts": "typescript", ".tsx": "tsx",
    ".rb": "ruby", ".rs": "rust", ".go": "go",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp",
    ".cs": "csharp", ".swift": "swift", ".m": "objectivec",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash", ".fish": "fish",
    ".html": "html", ".htm": "html", ".xml": "xml",
    ".css": "css", ".scss": "scss", ".less": "less",
    ".json": "json", ".jsonc": "json", ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".ini": "ini", ".env": "bash",
    ".md": "markdown", ".mdx": "markdown",
    ".sql": "sql", ".r": "r", ".R": "r",
    ".php": "php", ".pl": "perl", ".pm": "perl",
    ".lua": "lua", ".vim": "vim", ".ex": "elixir",
    ".hs": "haskell", ".ml": "ocaml", ".fs": "fsharp",
    ".dart": "dart", ".scala": "scala", ".clj": "clojure",
    ".tf": "hcl", ".hcl": "hcl",
}

def detectLanguage(filePath: str, firstLine: str) -> str:
    """Detect the programming language from file path + first line (shebang)."""
    if not filePath:
        return ""
    basename = os.path.basename(filePath)
    if basename in FILENAME_LANGS:
        return FILENAME_LANGS[basename]
    _, ext = os.path.splitext(basename)
    lang = EXT_LANGS.get(ext.lower(), "")
    if lang:
        return lang
    # shebang detection
    if firstLine.startswith("#!"):
        line = firstLine.lower()
        if "python" in line: return "python"
        if "ruby"   in line: return "ruby"
        if "node"   in line: return "javascript"
        if "bash"   in line or "sh" in line: return "bash"
        if "perl"   in line: return "perl"
    return ""

# ─── Syntax highlighting via Pygments ─────────────────────────────────────────

def _pygments_highlight(code: str, lang: str) -> list[tuple[str, str]]:
    """Return list of (scope, text) pairs using Pygments, or [] on failure."""
    try:
        from pygments import lex
        from pygments.lexers import get_lexer_by_name, guess_lexer
        from pygments.token import Token

        try:
            lexer = get_lexer_by_name(lang) if lang else guess_lexer(code)
        except Exception:
            return []

        tokens: list[tuple[str, str]] = []
        for ttype, value in lex(code, lexer):
            scope = _token_to_scope(ttype)
            tokens.append((scope, value))
        return tokens
    except ImportError:
        return []

def _token_to_scope(ttype: Any) -> str:
    """Map a Pygments token type to a TextMate-style scope name."""
    from pygments.token import (
        Token, Keyword, Name, Literal, String, Number,
        Operator, Punctuation, Comment, Generic,
    )
    if ttype in Keyword or ttype in Keyword.Declaration or ttype in Keyword.Namespace:
        return "keyword"
    if ttype in Keyword.Type:
        return "storage.type"
    if ttype in Name.Function:
        return "entity.name.function"
    if ttype in Name.Class:
        return "entity.name.class"
    if ttype in Name.Builtin:
        return "support.function"
    if ttype in String or ttype in Literal.String:
        return "string"
    if ttype in Number or ttype in Literal.Number:
        return "constant.numeric"
    if ttype in Comment:
        return "comment"
    if ttype in Operator:
        return "keyword.operator"
    if ttype in Punctuation:
        return "punctuation"
    return ""

def scopeColor(scope: str, scopes: dict[str, Color]) -> Optional[Color]:
    """Look up a scope in the theme, trying progressively shorter prefixes."""
    while scope:
        if scope in scopes:
            return scopes[scope]
        dot = scope.rfind(".")
        if dot < 0:
            break
        scope = scope[:dot]
    return None

def highlightLine(
    text: str,
    lang: str,
    theme: Theme,
) -> list[Block]:
    """Syntax-highlight one line and return a list of Blocks."""
    if not lang:
        fg = theme.foreground
        return [Block(text=text, fg=fg)]

    tokens = _pygments_highlight(text, lang)
    if not tokens:
        return [Block(text=text, fg=theme.foreground)]

    blocks: list[Block] = []
    for scope, value in tokens:
        if not value:
            continue
        color = scopeColor(scope, theme.scopes) if scope else None
        fg = color if color is not None else theme.foreground
        blocks.append(Block(text=value, fg=fg))
    return blocks

# ─── Word diff ────────────────────────────────────────────────────────────────

_TOKEN_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[^\s\w]|\s+')

def tokenize(text: str) -> list[str]:
    """Split text into word-diff tokens (identifiers, numbers, symbols, ws)."""
    return _TOKEN_RE.findall(text)

def findAdjacentPairs(markers: list[int]) -> list[tuple[int, int]]:
    """Find adjacent (del, add) index pairs in a flat marker list [idx1, idx2, ...]."""
    pairs: list[tuple[int, int]] = []
    i = 0
    while i + 1 < len(markers):
        pairs.append((markers[i], markers[i + 1]))
        i += 2
    return pairs

def wordDiffStrings(oldStr: str, newStr: str) -> tuple[list[str], list[str], list[tuple[int,int]]]:
    """Return (old_tokens, new_tokens, matching_ranges_in_old).

    matching_ranges_in_old: list of (start, end) token index ranges that are
    unchanged (used to colour only the changed words).
    """
    old_tokens = tokenize(oldStr)
    new_tokens = tokenize(newStr)
    matcher = difflib.SequenceMatcher(None, old_tokens, new_tokens, autojunk=False)
    matching: list[tuple[int, int]] = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            matching.append((i1, i2))
    return old_tokens, new_tokens, matching

# ─── Highlight pipeline helpers ────────────────────────────────────────────────

def removeNewlines(blocks: list[Block]) -> list[Block]:
    """Strip trailing newline from the last non-empty block."""
    out = list(blocks)
    if out and out[-1].text.endswith("\n"):
        last = out[-1]
        out[-1] = Block(text=last.text.rstrip("\n"), fg=last.fg, bg=last.bg,
                        bold=last.bold, dim=last.dim)
    return out

def _charWidth(ch: str) -> int:
    """Approximate display width of a character (1 for most, 2 for wide CJK)."""
    cp = ord(ch)
    if 0x1100 <= cp <= 0x115F or 0x2E80 <= cp <= 0x303E or \
       0x3040 <= cp <= 0x33FF or 0xFE10 <= cp <= 0xFE6F or \
       0xFF00 <= cp <= 0xFF60 or 0xFFE0 <= cp <= 0xFFE6 or \
       0x1F300 <= cp <= 0x1FAFF:
        return 2
    return 1

def _textWidth(s: str) -> int:
    return sum(_charWidth(c) for c in s)

def wrapText(blocks: list[Block], width: int, theme: Theme) -> list[list[Block]]:
    """Wrap blocks to a given column width. Returns list of lines."""
    if width <= 0:
        return [blocks]
    lines: list[list[Block]] = [[]]
    col = 0
    for b in blocks:
        remaining = b.text
        while remaining:
            if col >= width:
                lines.append([])
                col = 0
            space_left = width - col
            # How many chars fit?
            chars = 0
            w = 0
            for ch in remaining:
                cw = _charWidth(ch)
                if w + cw > space_left:
                    break
                w += cw
                chars += 1
            chunk = remaining[:chars]
            remaining = remaining[chars:]
            if chunk:
                lines[-1].append(Block(text=chunk, fg=b.fg, bg=b.bg,
                                       bold=b.bold, dim=b.dim))
                col += _textWidth(chunk)
    return lines

def addLineNumber(
    h: Highlight,
    theme: Theme,
    maxDigits: int,
    fullDim: bool,
) -> None:
    """Prepend line-number gutter blocks to each HighlightLine in place."""
    num_fg = theme.scopes.get("comment") or theme.foreground
    for hl in h:
        num = hl.lineNo
        if num is not None:
            gutter_text = f"{num:{maxDigits}d} "
        else:
            gutter_text = " " * (maxDigits + 1)
        hl.blocks.insert(0, Block(text=gutter_text, fg=num_fg, dim=fullDim))

def addMarker(h: Highlight, theme: Theme) -> None:
    """Prepend the diff marker ('+', '-', ' ') as a coloured block."""
    for hl in h:
        m = hl.marker
        if m == "+":
            fg = theme.addDecoration
        elif m == "-":
            fg = theme.deleteDecoration
        else:
            fg = theme.foreground
        hl.blocks.insert(0, Block(text=m + " ", fg=fg))

def dimContent(h: Highlight) -> None:
    """Dim all context lines (marker == ' ') in place."""
    for hl in h:
        if hl.marker == " ":
            for b in hl.blocks:
                b.dim = True

def applyBackground(h: Highlight, theme: Theme, wordDiffRanges: list[Any]) -> None:
    """Apply per-line and per-word background colours."""
    for i, hl in enumerate(h):
        m = hl.marker
        if m == "+":
            line_bg = theme.addLine
            word_bg = theme.addWord
        elif m == "-":
            line_bg = theme.deleteLine
            word_bg = theme.deleteWord
        else:
            continue  # context lines: no background

        # Apply line background to all blocks
        for b in hl.blocks:
            if b.bg is None:
                b.bg = line_bg

        # Apply word-level background from wordDiffRanges[i] if present
        if i < len(wordDiffRanges):
            ranges = wordDiffRanges[i]
            if ranges:
                # ranges: list of (col_start, col_end) character positions
                # We apply word_bg to blocks within those ranges
                col = 0
                for b in hl.blocks:
                    end = col + len(b.text)
                    for rs, re_ in ranges:
                        if col < re_ and end > rs:
                            b.bg = word_bg
                    col = end

def intoLines(h: Highlight, dim: bool, isFile: bool, mode: str) -> list[str]:
    """Convert a Highlight to a list of ANSI-escaped strings (one per line)."""
    result: list[str] = []
    for hl in h:
        skip_bg = isFile and hl.marker == " "
        line = asTerminalEscaped(hl.blocks, mode, skip_bg, dim and hl.marker == " ")
        result.append(line)
    return result

# ─── Public types ─────────────────────────────────────────────────────────────

@dataclass
class Hunk:
    oldStart: int
    oldLines: int
    newStart: int
    newLines: int
    lines: list[str]

@dataclass
class SyntaxTheme:
    theme: str
    source: Optional[str]

@dataclass
class NativeModule:
    ColorDiff: type
    ColorFile: type
    getSyntaxTheme: Any

# ─── ColorDiff ────────────────────────────────────────────────────────────────

class ColorDiff:
    """Renders a unified-diff hunk with syntax highlighting and word diff."""

    def __init__(
        self,
        hunk: Hunk,
        firstLine: str,
        filePath: str,
        prefixContent: Optional[str] = None,
    ) -> None:
        self.hunk = hunk
        self.firstLine = firstLine
        self.filePath = filePath
        self.prefixContent = prefixContent

    def render(self, themeName: str, width: int, dim: bool) -> Optional[list[str]]:
        """Render the hunk to a list of ANSI strings.

        Returns None if the hunk cannot be rendered.
        """
        try:
            mode = detectColorMode(themeName)
            theme = buildTheme(themeName, mode)
            lang = detectLanguage(self.filePath, self.firstLine)

            h: Highlight = []
            old_line = self.hunk.oldStart
            new_line = self.hunk.newStart

            del_lines: list[tuple[int, str]] = []  # (h_index, text)
            add_lines: list[tuple[int, str]] = []

            for raw in self.hunk.lines:
                if not raw:
                    continue
                marker = raw[0]
                text   = raw[1:] if len(raw) > 1 else ""
                blocks = removeNewlines(highlightLine(text, lang, theme))
                hl = HighlightLine(marker=marker, blocks=blocks)
                if marker == "-":
                    hl.lineNo = old_line
                    old_line += 1
                    del_lines.append((len(h), text))
                elif marker == "+":
                    hl.lineNo = new_line
                    new_line += 1
                    add_lines.append((len(h), text))
                else:
                    hl.lineNo = new_line
                    old_line += 1
                    new_line += 1
                h.append(hl)

            # Word diff: pair up del/add lines
            word_diff_ranges: list[list[tuple[int, int]]] = [[] for _ in h]
            min_pairs = min(len(del_lines), len(add_lines))
            for i in range(min_pairs):
                di, old_text = del_lines[i]
                ai, new_text = add_lines[i]
                old_toks, new_toks, matching = wordDiffStrings(old_text, new_text)
                # Build changed token ranges for old line
                matched_old = set()
                for rs, re_ in matching:
                    for j in range(rs, re_):
                        matched_old.add(j)
                col = 0
                del_ranges: list[tuple[int, int]] = []
                for j, tok in enumerate(old_toks):
                    end = col + len(tok)
                    if j not in matched_old and tok.strip():
                        del_ranges.append((col, end))
                    col = end
                # For new (add) line
                matched_new = set()
                for rs, re_ in matching:
                    for j in range(rs, re_):
                        matched_new.add(j)
                col = 0
                add_ranges: list[tuple[int, int]] = []
                for j, tok in enumerate(new_toks):
                    end = col + len(tok)
                    if j not in matched_new and tok.strip():
                        add_ranges.append((col, end))
                    col = end
                word_diff_ranges[di] = del_ranges
                word_diff_ranges[ai] = add_ranges

            # Max line number digits for gutter
            max_ln = max((hl.lineNo or 0) for hl in h) if h else 0
            max_digits = max(len(str(max_ln)), 1)

            addMarker(h, theme)
            applyBackground(h, theme, word_diff_ranges)
            addLineNumber(h, theme, max_digits, False)
            if dim:
                dimContent(h)

            return intoLines(h, dim, False, mode)
        except Exception:
            return None

# ─── ColorFile ────────────────────────────────────────────────────────────────

class ColorFile:
    """Renders a whole file with syntax highlighting (no diff markers)."""

    def __init__(self, code: str, filePath: str) -> None:
        self.code = code
        self.filePath = filePath

    def render(self, themeName: str, width: int, dim: bool) -> Optional[list[str]]:
        try:
            mode = detectColorMode(themeName)
            theme = buildTheme(themeName, mode)
            lines = self.code.splitlines(keepends=True)
            firstLine = lines[0] if lines else ""
            lang = detectLanguage(self.filePath, firstLine)

            h: Highlight = []
            for i, line in enumerate(lines, 1):
                blocks = removeNewlines(highlightLine(line, lang, theme))
                hl = HighlightLine(marker=" ", lineNo=i, blocks=blocks)
                h.append(hl)

            max_digits = max(len(str(len(lines))), 1)
            addLineNumber(h, theme, max_digits, dim)

            return intoLines(h, dim, True, mode)
        except Exception:
            return None

# ─── getSyntaxTheme / getNativeModule ─────────────────────────────────────────

def getSyntaxTheme(themeName: str) -> SyntaxTheme:
    """Return the SyntaxTheme to use.

    Respects vivian_CODE_SYNTAX_HIGHLIGHT and BAT_THEME env vars.
    """
    override = (
        os.environ.get("vivian_CODE_SYNTAX_HIGHLIGHT")
        or os.environ.get("BAT_THEME")
        or themeName
    )
    return SyntaxTheme(theme=defaultSyntaxThemeName(override), source=None)

_native_module_cache: Optional[NativeModule] = None

def getNativeModule() -> Optional[NativeModule]:
    """Return the NativeModule singleton (lazy-initialised, cached)."""
    global _native_module_cache
    if _native_module_cache is None:
        _native_module_cache = NativeModule(
            ColorDiff=ColorDiff,
            ColorFile=ColorFile,
            getSyntaxTheme=getSyntaxTheme,
        )
    return _native_module_cache

# ─── __test (internal helpers exposed for unit tests) ─────────────────────────

__test = {
    "tokenize":         tokenize,
    "findAdjacentPairs": findAdjacentPairs,
    "wordDiffStrings":  wordDiffStrings,
    "ansi256FromRgb":   ansi256FromRgb,
    "colorToEscape":    colorToEscape,
    "detectColorMode":  detectColorMode,
    "detectLanguage":   detectLanguage,
}
