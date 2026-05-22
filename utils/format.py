"""Formatting utilities — mirrors src/utils/format.ts."""

from __future__ import annotations


def format_duration(ms: float) -> str:
    """Format milliseconds to human-readable duration."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    elif ms < 60000:
        return f"{ms / 1000:.1f}s"
    else:
        minutes = ms / 60000
        if minutes < 60:
            return f"{minutes:.1f}m"
        else:
            return f"{minutes / 60:.1f}h"


def format_number(n: int) -> str:
    """Format a number with commas."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def format_cost(cost: float, max_decimal_places: int = 4) -> str:
    """Format a USD cost."""
    if cost > 0.5:
        return f"${cost:.2f}"
    return f"${cost:.{max_decimal_places}f}"


def format_bytes(size: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def truncate(text: str, max_chars: int, suffix: str = "...") -> str:
    """Truncate text to max_chars, adding suffix if truncated."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - len(suffix)] + suffix


def format_table(rows: list[list[str]], headers: Optional[list[str]] = None) -> str:
    """Format data as an ASCII table."""
    if not rows:
        return ""

    all_rows = [headers] + rows if headers else rows
    col_widths = [
        max(len(str(row[i])) for row in all_rows if i < len(row))
        for i in range(max(len(row) for row in all_rows))
    ]

    def format_row(row: list[str]) -> str:
        cells = [
            str(row[i]).ljust(col_widths[i]) if i < len(row) else " " * col_widths[i]
            for i in range(len(col_widths))
        ]
        return " | ".join(cells)

    lines = []
    if headers:
        lines.append(format_row(headers))
        lines.append("-+-".join("-" * w for w in col_widths))

    for row in rows:
        lines.append(format_row(row))

    return "\n".join(lines)


from typing import Optional
