"""Port of src/ink/widest-line.ts."""
from .line_width_cache import lineWidth


def widestLine(string: str) -> int:
    max_width = 0
    start = 0

    while start <= len(string):
        end = string.find("\n", start)
        line = string[start:end] if end != -1 else string[start:]

        max_width = max(max_width, lineWidth(line))

        if end == -1:
            break
        start = end + 1

    return max_width


widest_line = widestLine
