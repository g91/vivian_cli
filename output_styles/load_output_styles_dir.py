"""Load output styles from a project directory — mirrors
src/outputStyles/loadOutputStylesDir.ts.

Output styles are markdown files in an `output-styles/` subdirectory of the
project root. Each file becomes an OutputStyleConfig that instructs the model
how to format its responses.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

log = logging.getLogger(__name__)

# Module-level memo cache: cwd → list[OutputStyleConfig]
_cache: dict[str, list[dict]] = {}


async def getOutputStyleDirStyles(cwd: str) -> list[dict]:
    """Return output style configs loaded from `{cwd}/output-styles/`.

    Results are memoized by cwd for the lifetime of the process (cleared by
    clearOutputStyleCaches).
    """
    if cwd in _cache:
        return _cache[cwd]

    styles: list[dict] = []

    try:
        from vivian_cli.output_styles.utils import (
            loadMarkdownFilesForSubdir,
            coerceDescriptionToString,
            extractDescriptionFromMarkdown,
        )
    except ImportError:
        _cache[cwd] = styles
        return styles

    try:
        files = await loadMarkdownFilesForSubdir("output-styles", cwd)
    except Exception as exc:
        log.debug("loadOutputStylesDir: %s", exc)
        _cache[cwd] = styles
        return styles

    for file in files:
        name = file.get("name", "")
        content = file.get("content", "")
        frontmatter = file.get("frontmatter", {})
        source = file.get("source", "dir")

        description_raw = frontmatter.get("description") or extractDescriptionFromMarkdown(content)
        description = coerceDescriptionToString(description_raw)

        if "force-for-plugin" in frontmatter:
            log.warning(
                "Output style %r has 'force-for-plugin' but is not a plugin style — "
                "the key will be ignored.",
                name,
            )

        keep_coding = frontmatter.get("keepCodingInstructions", False)

        styles.append({
            "name": name,
            "description": description,
            "prompt": content.strip(),
            "source": source,
            "keepCodingInstructions": bool(keep_coding),
        })

    _cache[cwd] = styles
    return styles


def clearOutputStyleCaches() -> None:
    """Clear all output-style caches (getOutputStyleDirStyles memoisation +
    loadMarkdownFilesForSubdir memoisation + plugin style cache).
    """
    _cache.clear()

    try:
        from vivian_cli.output_styles.utils import clearMarkdownSubdirCache
        clearMarkdownSubdirCache()
    except Exception:
        pass

    try:
        from vivian_cli.output_styles.plugin_styles import clearPluginOutputStyleCache
        clearPluginOutputStyleCache()
    except Exception:
        pass
