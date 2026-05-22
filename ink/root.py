"""Port of src/ink/root.ts."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

from .ink import Ink, Options
from .instances import get_instance, set_instance, delete_instance


@dataclass(slots=True)
class RenderOptions:
    stdout: Any = sys.stdout
    stdin: Any = sys.stdin
    stderr: Any = sys.stderr
    exitOnCtrlC: bool = True
    patchConsole: bool = True
    onFrame: Any = None


@dataclass(slots=True)
class Instance:
    rerender: Any
    unmount: Any
    waitUntilExit: Any
    cleanup: Any


@dataclass(slots=True)
class Root:
    render: Any
    unmount: Any
    waitUntilExit: Any


def renderSync(node: Any, options: Any | None = None) -> Instance:
    opts = getOptions(options)
    ink_options = Options(
        stdout=opts.stdout,
        stdin=opts.stdin,
        stderr=opts.stderr,
        exitOnCtrlC=opts.exitOnCtrlC,
        patchConsole=opts.patchConsole,
        onFrame=opts.onFrame,
    )
    instance = getInstance(ink_options.stdout, lambda: Ink(ink_options))
    instance.render(node)
    return Instance(
        rerender=instance.render,
        unmount=instance.unmount,
        waitUntilExit=instance.waitUntilExit,
        cleanup=lambda: delete_instance(_stdout_fd(ink_options.stdout)),
    )


async def render(node: Any, options: Any | None = None) -> Instance:
    return renderSync(node, options)


async def createRoot(options: RenderOptions | None = None) -> Root:
    opts = options or RenderOptions()
    instance = Ink(Options(
        stdout=opts.stdout,
        stdin=opts.stdin,
        stderr=opts.stderr,
        exitOnCtrlC=opts.exitOnCtrlC,
        patchConsole=opts.patchConsole,
        onFrame=opts.onFrame,
    ))
    set_instance(_stdout_fd(opts.stdout), instance)
    return Root(
        render=instance.render,
        unmount=instance.unmount,
        waitUntilExit=instance.waitUntilExit,
    )


def getOptions(stdout: Any | None = None) -> RenderOptions:
    if stdout is None:
        return RenderOptions()
    if hasattr(stdout, "write") and not isinstance(stdout, RenderOptions):
        return RenderOptions(stdout=stdout, stdin=sys.stdin)
    return stdout


def getInstance(stdout: Any, createInstance: Any) -> Ink:
    instance = get_instance(_stdout_fd(stdout))
    if instance is None:
        instance = createInstance()
        set_instance(_stdout_fd(stdout), instance)
    return instance


def _stdout_fd(stdout: Any) -> int:
    fileno = getattr(stdout, "fileno", None)
    if callable(fileno):
        try:
            return int(fileno())
        except OSError:
            return id(stdout)
    return id(stdout)
