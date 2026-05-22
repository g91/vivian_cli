"""Port of src/ink/Ansi.tsx - ANSI escape code parser and renderer."""
from __future__ import annotations

from typing import Any

from .termio.parser import Parser
from .termio.types import TextStyle, NamedColor, Color as TermioColor

NAMED_COLOR_MAP: dict[str, str] = {
    "black": "ansi:black", "red": "ansi:red", "green": "ansi:green",
    "yellow": "ansi:yellow", "blue": "ansi:blue", "magenta": "ansi:magenta",
    "cyan": "ansi:cyan", "white": "ansi:white",
    "brightBlack": "ansi:blackBright", "brightRed": "ansi:redBright",
    "brightGreen": "ansi:greenBright", "brightYellow": "ansi:yellowBright",
    "brightBlue": "ansi:blueBright", "brightMagenta": "ansi:magentaBright",
    "brightCyan": "ansi:cyanBright", "brightWhite": "ansi:whiteBright",
}

SpanProps = dict[str, Any]
Span = dict[str, Any]


def _colorToString(color: TermioColor | None) -> str | None:
    if not color:
        return None
    if isinstance(color, dict):
        t = color.get("type")
        if t == "named":
            return NAMED_COLOR_MAP.get(color.get("name", ""))
        if t == "indexed":
            return f"ansi256({color.get('index', 0)})"
        if t == "rgb":
            return f"rgb({color.get('r', 0)},{color.get('g', 0)},{color.get('b', 0)})"
    return None


def _textStyleToSpanProps(style: TextStyle) -> SpanProps:
    props: SpanProps = {}
    fg = _colorToString(style.fg)
    if fg:
        props["color"] = fg
    bg = _colorToString(style.bg)
    if bg:
        props["backgroundColor"] = bg
    if style.bold:
        props["bold"] = True
    if style.dim:
        props["dim"] = True
    if style.italic:
        props["italic"] = True
    if style.underline:
        props["underline"] = True
    if style.strikethrough:
        props["strikethrough"] = True
    if style.inverse:
        props["inverse"] = True
    return props


def _propsEqual(a: SpanProps, b: SpanProps) -> bool:
    return a == b


def _hasAnyProps(props: SpanProps) -> bool:
    return any(v for v in props.values())


def parseToSpans(input: str) -> list[Span]:
    parser = Parser()
    actions = parser.feed(input)
    actions.extend(parser.flush())

    spans: list[Span] = []
    for action in actions:
        if action.get("type") == "text":
            graphemes = action.get("graphemes", [])
            text = "".join(g.get("text", "") for g in graphemes)
            style = action.get("style")
            if style:
                props = _textStyleToSpanProps(style)
                spans.append({"text": text, "props": props})
        elif action.get("type") == "link":
            spans.append({"text": "", "props": {"hyperlink": action.get("uri")}})

    # Merge adjacent spans with equal props
    merged: list[Span] = []
    for span in spans:
        if merged and _propsEqual(merged[-1]["props"], span["props"]):
            merged[-1]["text"] += span["text"]
        else:
            merged.append(span)

    return merged
