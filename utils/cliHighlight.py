"""CLI syntax highlighting — mirrors src/utils/cliHighlight.ts"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional


CliHighlight = dict[str, Callable[..., Any]]

_cli_highlight_promise: CliHighlight | None | object = object()
_loaded_get_language: Callable[[str], Any] | None = None


def _load_cli_highlight() -> CliHighlight | None:
    global _loaded_get_language
    try:
        from pygments import highlight as pygments_highlight
        from pygments.formatters import TerminalFormatter
        from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
        from pygments.util import ClassNotFound
    except Exception:
        return None

    def _highlight(code: str, language: str | None = None, **_: Any) -> str:
        try:
            lexer = get_lexer_by_name(language) if language else get_lexer_by_name('text')
        except Exception:
            try:
                lexer = get_lexer_by_name('text')
            except Exception:
                return code
        try:
            return pygments_highlight(code, lexer, TerminalFormatter()).rstrip('\n')
        except Exception:
            return code

    def _supports_language(language: str) -> bool:
        try:
            get_lexer_by_name(language)
            return True
        except Exception:
            return False

    def _get_language(file_path: str) -> Any:
        try:
            return get_lexer_for_filename(file_path)
        except ClassNotFound:
            return None
        except Exception:
            return None

    _loaded_get_language = _get_language
    return {
        'highlight': _highlight,
        'supportsLanguage': _supports_language,
    }


async def getCliHighlightPromise() -> CliHighlight | None:
    global _cli_highlight_promise
    if _cli_highlight_promise.__class__ is object:
        _cli_highlight_promise = _load_cli_highlight()
    return _cli_highlight_promise  # type: ignore[return-value]


async def getLanguageName(file_path: str) -> str:
    await getCliHighlightPromise()
    ext = Path(file_path).suffix
    if not ext:
        return 'unknown'
    if _loaded_get_language is None:
        return 'unknown'
    language = _loaded_get_language(file_path)
    name = getattr(language, 'name', None)
    return name if isinstance(name, str) and name else 'unknown'


async def get_highlight_fn(language: Optional[str] = None) -> Optional[Callable[..., Any]]:
    cli_highlight = await getCliHighlightPromise()
    if not cli_highlight:
        return None

    def _highlight(code: str) -> str:
        return cli_highlight['highlight'](code, language)

    return _highlight


get_cli_highlight_promise = getCliHighlightPromise
get_language_name = getLanguageName
