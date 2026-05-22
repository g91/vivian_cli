"""Port of src/ink/measure-text.ts."""
from .line_width_cache import lineWidth


def measureText(text: str, maxWidth: int = 0) -> dict[str, int]:
    if not text:
        return {"width": 0, "height": 0}

    no_wrap = maxWidth <= 0

    height = 0
    width = 0
    start = 0

    while start <= len(text):
        end = text.find("\n", start)
        line = text[start:end] if end != -1 else text[start:]

        w = lineWidth(line)
        width = max(width, w)

        if no_wrap:
            height += 1
        else:
            height += 1 if w == 0 else max(1, (w + maxWidth - 1) // maxWidth)

        if end == -1:
            break
        start = end + 1

    return {"width": width, "height": height}


measure_text = measureText
