"""Port of src/utils/telemetry/logger.ts."""
from __future__ import annotations

from ..debug import logForDebugging
from ..log import logError


class vivianCodeDiagLogger:
    def error(self, message: str, *_: object) -> None:
        logError(Exception(str(message)))
        logForDebugging(f"[3P telemetry] OTEL diag error: {message}", level="error")

    def warn(self, message: str, *_: object) -> None:
        logError(Exception(str(message)))
        logForDebugging(f"[3P telemetry] OTEL diag warn: {message}", level="warn")

    def info(self, _message: str, *_args: object) -> None:
        return None

    def debug(self, _message: str, *_args: object) -> None:
        return None

    def verbose(self, _message: str, *_args: object) -> None:
        return None


vivian_code_diag_logger = vivianCodeDiagLogger

