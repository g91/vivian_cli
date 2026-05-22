"""Port of src/ink/line-width-cache.ts."""
from .stringWidth import stringWidth

_cache: dict[str, int] = {}
MAX_CACHE_SIZE = 4096


def lineWidth(line: str) -> int:
    cached = _cache.get(line)
    if cached is not None:
        return cached

    width = stringWidth(line)

    if len(_cache) >= MAX_CACHE_SIZE:
        _cache.clear()

    _cache[line] = width
    return width


line_width = lineWidth
