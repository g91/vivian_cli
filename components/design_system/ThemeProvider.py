"""Theme provider helpers — minimal port of src/components/design-system/ThemeProvider.tsx."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Callable, Iterator

from ...utils.theme import ThemeName, ThemeSetting


@dataclass(slots=True)
class _PreviewThemeControls:
    setPreviewTheme: Callable[[ThemeSetting], None]
    savePreview: Callable[[], None]
    cancelPreview: Callable[[], None]


_DEFAULT_THEME: ThemeName = "dark"
_THEME_SETTING: ContextVar[ThemeSetting] = ContextVar("design_system_theme_setting", default=_DEFAULT_THEME)
_CURRENT_THEME: ContextVar[ThemeName] = ContextVar("design_system_current_theme", default=_DEFAULT_THEME)
_PREVIEW_THEME: ContextVar[ThemeSetting | None] = ContextVar("design_system_preview_theme", default=None)


def _resolve_theme(setting: ThemeSetting) -> ThemeName:
    if setting == "auto":
        return _DEFAULT_THEME
    return setting


def useTheme() -> tuple[ThemeName, Callable[[ThemeSetting], None]]:
    def setThemeSetting(setting: ThemeSetting) -> None:
        _THEME_SETTING.set(setting)
        _CURRENT_THEME.set(_resolve_theme(setting))
        _PREVIEW_THEME.set(None)

    return (_CURRENT_THEME.get(), setThemeSetting)


def useThemeSetting() -> ThemeSetting:
    return _THEME_SETTING.get()


def usePreviewTheme() -> _PreviewThemeControls:
    previous_setting = _THEME_SETTING.get()

    def setPreviewTheme(setting: ThemeSetting) -> None:
        _PREVIEW_THEME.set(setting)
        _CURRENT_THEME.set(_resolve_theme(setting))

    def savePreview() -> None:
        preview = _PREVIEW_THEME.get()
        if preview is None:
            return
        _THEME_SETTING.set(preview)
        _CURRENT_THEME.set(_resolve_theme(preview))
        _PREVIEW_THEME.set(None)

    def cancelPreview() -> None:
        _PREVIEW_THEME.set(None)
        _CURRENT_THEME.set(_resolve_theme(previous_setting))

    return _PreviewThemeControls(
        setPreviewTheme=setPreviewTheme,
        savePreview=savePreview,
        cancelPreview=cancelPreview,
    )


@contextmanager
def ThemeProvider(themeName: ThemeSetting = _DEFAULT_THEME) -> Iterator[None]:
    setting_token: Token[ThemeSetting] = _THEME_SETTING.set(themeName)
    current_token: Token[ThemeName] = _CURRENT_THEME.set(_resolve_theme(themeName))
    preview_token: Token[ThemeSetting | None] = _PREVIEW_THEME.set(None)
    try:
        yield None
    finally:
        _PREVIEW_THEME.reset(preview_token)
        _CURRENT_THEME.reset(current_token)
        _THEME_SETTING.reset(setting_token)


__all__ = ["ThemeProvider", "usePreviewTheme", "useTheme", "useThemeSetting"]