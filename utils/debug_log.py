"""Vivian debug logging — writes to ~/.vivian/debug.log when enabled.

Enable programmatically (TUI/web GUI start):
    from vivian_cli.utils.debug_log import enable_debug, dlog
    enable_debug()

Or via environment variable (any mode):
    VIVIAN_DEBUG=1 python -m vivian_cli

Tail the log in a second terminal:
    tail -f ~/.vivian/debug.log
"""
from __future__ import annotations
import logging
import os
import sys
from pathlib import Path

_LOG_PATH = Path.home() / ".vivian" / "debug.log"

# Module-level state
_enabled: bool = False
_logger = logging.getLogger("vivian.debug")
_logger.propagate = False


def enable_debug(to_file: bool = True) -> None:
    """Enable debug logging.  Call once at startup in TUI / web-GUI mode."""
    global _enabled
    if _enabled:
        return
    _enabled = True
    _logger.setLevel(logging.DEBUG)
    _logger.propagate = False

    if not _logger.handlers:
        if to_file:
            try:
                _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                fh = logging.FileHandler(str(_LOG_PATH), mode="a", encoding="utf-8")
                fh.setFormatter(
                    logging.Formatter(
                        "%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S",
                    )
                )
                _logger.addHandler(fh)
            except Exception:
                to_file = False

        if not to_file:
            sh = logging.StreamHandler(sys.stderr)
            sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            _logger.addHandler(sh)

    dlog(f"=== Vivian debug logging enabled → {_LOG_PATH} ===")


def is_enabled() -> bool:
    return _enabled or bool(os.environ.get("VIVIAN_DEBUG"))


def dlog(msg: str, *args: object) -> None:
    """Write a debug line.  No-op when disabled (zero overhead)."""
    if not (_enabled or os.environ.get("VIVIAN_DEBUG")):
        return
    # If env-var path is used without programmatic enable, fall back to the
    # legacy file so existing users aren't surprised.
    if not _enabled and os.environ.get("VIVIAN_DEBUG"):
        _legacy_write(msg % args if args else msg)
        return
    _logger.debug(msg, *args)


def dlog_exc(label: str, exc: BaseException) -> None:
    """Log an exception with traceback."""
    if not is_enabled():
        return
    import traceback
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    dlog(f"{label}  EXCEPTION: {type(exc).__name__}: {exc}\n{tb}")


def _legacy_write(msg: str) -> None:
    """Write to the legacy ~/.vivian_cli_debug.log path (VIVIAN_DEBUG env var)."""
    try:
        import time
        with open(os.path.expanduser("~/.vivian_cli_debug.log"), "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass
