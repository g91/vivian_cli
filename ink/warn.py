"""Port of src/ink/warn.ts."""
from ..utils.debug import logForDebugging


def ifNotInteger(value: int | float | None, name: str) -> None:
    if value is None:
        return
    if isinstance(value, int):
        return
    logForDebugging(f"{name} should be an integer, got {value}", level="warn")


if_not_integer = ifNotInteger
