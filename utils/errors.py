"""Error types and helpers — mirrors src/utils/errors.ts"""
from __future__ import annotations

from typing import Optional


class vivianError(Exception):
    """Base error for Vivian CLI errors."""
    pass


class MalformedCommandError(Exception):
    """Raised when a user command cannot be parsed."""
    pass


class AbortError(Exception):
    """Raised when the user or AbortController aborts an operation."""
    pass


class ConfigParseError(Exception):
    """Raised when a configuration file cannot be parsed."""

    def __init__(self, message: str, file_path: str, default_config) -> None:
        super().__init__(message)
        self.file_path = file_path
        self.default_config = default_config


class ShellError(Exception):
    """Raised when a shell command fails."""

    def __init__(self, stdout: str, stderr: str, code: int, interrupted: bool) -> None:
        super().__init__("Shell command failed")
        self.stdout = stdout
        self.stderr = stderr
        self.code = code
        self.interrupted = interrupted


class TeleportOperationError(Exception):
    """Raised on a Teleport operation failure."""

    def __init__(self, message: str, formatted_message: str) -> None:
        super().__init__(message)
        self.formatted_message = formatted_message


class TelemetrySafeError(Exception):
    """Error whose message is safe to log to telemetry."""

    def __init__(self, message: str, telemetry_message: Optional[str] = None) -> None:
        super().__init__(message)
        self.telemetry_message = telemetry_message or message


def is_abort_error(e: object) -> bool:
    """Return True if e is any abort-shaped error."""
    if isinstance(e, AbortError):
        return True
    if isinstance(e, Exception) and type(e).__name__ == "AbortError":
        return True
    return False


def has_exact_error_message(error: object, message: str) -> bool:
    """Return True if error is an Exception with exactly the given message."""
    return isinstance(error, Exception) and str(error) == message


def to_error(e: object) -> Exception:
    """Normalize an unknown value into an Exception."""
    return e if isinstance(e, Exception) else Exception(str(e))


def error_message(e: object) -> str:
    """Extract a string message from an unknown error-like value."""
    return str(e) if isinstance(e, Exception) else str(e)


def get_errno_code(e: object) -> Optional[str]:
    """Extract the errno code string (e.g. 'ENOENT') from an OSError."""
    if isinstance(e, OSError):
        import errno as _errno
        # Map Python errno numbers back to POSIX constant names
        mapping = {getattr(_errno, n): n for n in dir(_errno) if n.startswith("E")}
        return mapping.get(e.errno)
    _val = e
    if _val is None: return ""
    return str(_val)


def is_enoent(e: object) -> bool:
    """Return True if e is a FileNotFoundError / ENOENT."""
    return isinstance(e, FileNotFoundError) or get_errno_code(e) == "ENOENT"


def get_errno_path(e: object) -> Optional[str]:
    """Extract the filesystem path from an OSError."""
    if isinstance(e, OSError) and e.filename:
        return str(e.filename)
    _val = e
    if _val is None: return ""
    return str(_val)


# TypeScript-port compatibility aliases
isAbortError = is_abort_error
hasExactErrorMessage = has_exact_error_message
toError = to_error
errorMessage = error_message
getErrnoCode = get_errno_code
isENOENT = is_enoent
getErrnoPath = get_errno_path
