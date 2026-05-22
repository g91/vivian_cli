"""Port of src/ink/components/ErrorOverview.tsx."""
from __future__ import annotations

import traceback


def renderErrorOverview(error: BaseException) -> str:
    message = f"{type(error).__name__}: {error}"
    formatted = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    return f"{message}\n{formatted}".rstrip()


class ErrorOverview:
    def __init__(self, error: BaseException) -> None:
        self.error = error

    def render(self) -> str:
        return renderErrorOverview(self.error)

    def __str__(self) -> str:
        return self.render()
