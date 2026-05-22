"""Port of src/ink/instances.ts."""
from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from .ink import Ink

_instances: dict[int, Ink] = {}


def get_instance(stdout_fd: int) -> Ink | None:
    return _instances.get(stdout_fd)


def set_instance(stdout_fd: int, instance: Ink) -> None:
    _instances[stdout_fd] = instance


def delete_instance(stdout_fd: int) -> None:
    _instances.pop(stdout_fd, None)
