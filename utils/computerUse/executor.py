"""Port of src/utils/computerUse/executor.ts."""
from __future__ import annotations

import asyncio
import math
import os
import sys
from typing import Any

from ..debug import logForDebugging
from .common import CLI_CU_CAPABILITIES, CLI_HOST_BUNDLE_ID, getTerminalBundleId
from .drainRunLoop import drainRunLoop
from .inputLoader import requireComputerUseInput
from .swiftLoader import requireComputerUseSwift

SCREENSHOT_JPEG_QUALITY = 0.75
MOVE_SETTLE_MS = 50

# Default API resize params — max dimensions for screenshots sent to the API
API_RESIZE_PARAMS = {"maxWidth": 1568, "maxHeight": 1568}


def computeTargetDims(logicalW: float, logicalH: float, scaleFactor: float) -> tuple[int, int]:
    physW = round(logicalW * scaleFactor)
    physH = round(logicalH * scaleFactor)
    return _targetImageSize(physW, physH, API_RESIZE_PARAMS)


def _targetImageSize(physW: int, physH: int, params: dict[str, int]) -> tuple[int, int]:
    maxW = params.get("maxWidth", 1568)
    maxH = params.get("maxHeight", 1568)
    if physW <= maxW and physH <= maxH:
        return (physW, physH)
    scale = min(maxW / physW, maxH / physH)
    return (round(physW * scale), round(physH * scale))


async def readClipboardViaPbpaste() -> str:
    if sys.platform != "darwin":
        raise RuntimeError("pbpaste is macOS-only")
    proc = await asyncio.create_subprocess_exec(
        "pbpaste",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"pbpaste exited with code {proc.returncode}: {stderr.decode()}")
    return stdout.decode("utf-8")


async def writeClipboardViaPbcopy(text: str) -> None:
    if sys.platform != "darwin":
        raise RuntimeError("pbcopy is macOS-only")
    proc = await asyncio.create_subprocess_exec(
        "pbcopy",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=text.encode("utf-8"))
    if proc.returncode != 0:
        raise RuntimeError(f"pbcopy exited with code {proc.returncode}: {stderr.decode()}")


def isBareEscape(parts: list[str]) -> bool:
    if len(parts) != 1:
        return False
    lower = parts[0].lower()
    return lower in ("escape", "esc")


async def moveAndSettle(input_module: Any, x: float, y: float) -> None:
    await input_module.moveMouse(x, y, False)
    await asyncio.sleep(MOVE_SETTLE_MS / 1000)


async def releasePressed(input_module: Any, pressed: list[str]) -> None:
    while pressed:
        k = pressed.pop()
        try:
            await input_module.key(k, "release")
        except Exception:
            pass


async def withModifiers(input_module: Any, mods: list[str], fn: Any) -> Any:
    pressed: list[str] = []
    try:
        for m in mods:
            await input_module.key(m, "press")
            pressed.append(m)
        result = fn()
        if asyncio.iscoroutine(result):
            return await result
        return result
    finally:
        await releasePressed(input_module, pressed)


async def typeViaClipboard(input_module: Any, text: str) -> None:
    saved: str | None = None
    try:
        saved = await readClipboardViaPbpaste()
    except Exception:
        logForDebugging("[computer-use] pbpaste before paste failed; proceeding without restore")

    try:
        await writeClipboardViaPbcopy(text)
        if (await readClipboardViaPbpaste()) != text:
            raise RuntimeError("Clipboard write verification failed")
        await input_module.keys(["command", "v"])
        await asyncio.sleep(0.1)
    finally:
        if saved is not None:
            try:
                await writeClipboardViaPbcopy(saved)
            except Exception:
                pass


async def animatedMove(
    input_module: Any,
    targetX: float,
    targetY: float,
    mouseAnimationEnabled: bool,
) -> None:
    if not mouseAnimationEnabled:
        await moveAndSettle(input_module, targetX, targetY)
        return

    start = await input_module.mouseLocation()
    deltaX = targetX - start["x"]
    deltaY = targetY - start["y"]
    distance = math.hypot(deltaX, deltaY)
    if distance < 1:
        return

    duration_sec = min(distance / 2000, 0.5)
    if duration_sec < 0.03:
        await moveAndSettle(input_module, targetX, targetY)
        return

    frame_rate = 60
    frame_interval = 1.0 / frame_rate
    total_frames = math.floor(duration_sec * frame_rate)

    for frame in range(1, total_frames + 1):
        t = frame / total_frames
        eased = 1 - math.pow(1 - t, 3)
        await input_module.moveMouse(
            round(start["x"] + deltaX * eased),
            round(start["y"] + deltaY * eased),
            False,
        )
        if frame < total_frames:
            await asyncio.sleep(frame_interval)

    await asyncio.sleep(MOVE_SETTLE_MS / 1000)


def createCliExecutor(opts: dict[str, Any] | None = None) -> dict[str, Any]:
    if opts is None:
        opts = {}

    if sys.platform != "darwin":
        raise RuntimeError(f"createCliExecutor called on {sys.platform}. Computer control is macOS-only.")

    cu = requireComputerUseSwift()
    get_mouse_animation_enabled = opts.get("getMouseAnimationEnabled", lambda: True)
    get_hide_before_action_enabled = opts.get("getHideBeforeActionEnabled", lambda: True)

    terminal_bundle_id = getTerminalBundleId()
    surrogate_host = terminal_bundle_id or CLI_HOST_BUNDLE_ID

    def without_terminal(allowed: list[str]) -> list[str]:
        if terminal_bundle_id is None:
            return list(allowed)
        return [id for id in allowed if id != terminal_bundle_id]

    logForDebugging(
        f"[computer-use] terminal {terminal_bundle_id} -> surrogate host (hide-exempt, activate-skip, screenshot-excluded)"
        if terminal_bundle_id
        else "[computer-use] terminal not detected; falling back to sentinel host"
    )

    executor: dict[str, Any] = {
        "capabilities": {
            **CLI_CU_CAPABILITIES,
            "hostBundleId": CLI_HOST_BUNDLE_ID,
        },
    }

    # ── Pre-action sequence ────────────────────────────────────────────

    async def prepareForAction(allowlistBundleIds: list[str], displayId: int | None = None) -> list[str]:
        if not get_hide_before_action_enabled():
            return []
        filtered = without_terminal(allowlistBundleIds)
        return await drainRunLoop(lambda: cu.apps.hideOthers(filtered, displayId))

    async def previewHideSet(allowlistBundleIds: list[str], displayId: int | None = None) -> list[dict[str, str]]:
        filtered = without_terminal(allowlistBundleIds)
        return await drainRunLoop(lambda: cu.apps.previewHideSet(filtered, displayId))

    executor["prepareForAction"] = prepareForAction
    executor["previewHideSet"] = previewHideSet

    # ── Display ──────────────────────────────────────────────────────────

    async def getDisplaySize(displayId: int | None = None) -> dict[str, Any]:
        return await drainRunLoop(lambda: cu.display.getSize(displayId))

    async def listDisplays() -> list[dict[str, Any]]:
        return await drainRunLoop(lambda: cu.display.listDisplays())

    async def findWindowDisplays(bundleIds: list[str]) -> list[dict[str, Any]]:
        return await drainRunLoop(lambda: cu.apps.findWindowDisplays(bundleIds))

    async def resolvePrepareCapture(opts_in: dict[str, Any]) -> dict[str, Any]:
        return await drainRunLoop(lambda: cu.capture.resolvePrepareCapture(
            without_terminal(opts_in.get("allowedBundleIds", [])),
            opts_in.get("preferredDisplayId"),
            opts_in.get("autoResolve", False),
            opts_in.get("doHide", False),
        ))

    executor["getDisplaySize"] = getDisplaySize
    executor["listDisplays"] = listDisplays
    executor["findWindowDisplays"] = findWindowDisplays
    executor["resolvePrepareCapture"] = resolvePrepareCapture

    # ── Screenshot ───────────────────────────────────────────────────────

    async def screenshot(opts_in: dict[str, Any]) -> dict[str, Any]:
        allowed = without_terminal(opts_in.get("allowedBundleIds", []))
        display_id = opts_in.get("displayId")
        result = await drainRunLoop(lambda: cu.capture.captureExcluding(allowed, display_id))
        target_w, target_h = computeTargetDims(
            result.get("logicalWidth", result.get("width", 0)),
            result.get("logicalHeight", result.get("height", 0)),
            result.get("scaleFactor", 2.0),
        )
        return {
            "base64": result.get("base64", ""),
            "width": target_w,
            "height": target_h,
            "displayId": result.get("displayId", 0),
            "displayWidth": result.get("displayWidth", 0),
            "displayHeight": result.get("displayHeight", 0),
            "originX": result.get("originX", 0),
            "originY": result.get("originY", 0),
        }

    async def zoom(regionLogical: dict[str, float], allowedBundleIds: list[str], displayId: int | None = None) -> dict[str, Any]:
        allowed = without_terminal(allowedBundleIds)
        result = await drainRunLoop(lambda: cu.capture.captureRegion(
            regionLogical["x"], regionLogical["y"],
            regionLogical["w"], regionLogical["h"],
            allowed, displayId,
        ))
        return {
            "base64": result.get("base64", ""),
            "width": result.get("width", 0),
            "height": result.get("height", 0),
        }

    executor["screenshot"] = screenshot
    executor["zoom"] = zoom

    # ── Keyboard ─────────────────────────────────────────────────────────

    async def key(text: str) -> dict[str, Any]:
        input_mod = requireComputerUseInput()
        parts = text.split("+") if "+" in text else [text]
        if isBareEscape(parts):
            from .escHotkey import notifyExpectedEscape
            notifyExpectedEscape()
        await drainRunLoop(lambda: input_mod.keys(parts))
        return {"content": [{"type": "text", "text": f"Pressed {text}"}]}

    async def holdKey(text: str) -> dict[str, Any]:
        input_mod = requireComputerUseInput()
        parts = text.split("+") if "+" in text else [text]
        await drainRunLoop(lambda: input_mod.key(parts[0], "press"))
        return {"content": [{"type": "text", "text": f"Holding {text}"}]}

    async def type_text(text: str) -> dict[str, Any]:
        input_mod = requireComputerUseInput()
        await drainRunLoop(lambda: typeViaClipboard(input_mod, text))
        return {"content": [{"type": "text", "text": f"Typed {len(text)} chars"}]}

    executor["key"] = key
    executor["holdKey"] = holdKey
    executor["type"] = type_text

    # ── Mouse ────────────────────────────────────────────────────────────

    async def leftClick(coordinate: list[float]) -> dict[str, Any]:
        input_mod = requireComputerUseInput()
        x, y = coordinate[0], coordinate[1]
        await drainRunLoop(lambda: _do_click(input_mod, x, y, "left"))
        return {"content": [{"type": "text", "text": f"Clicked ({x}, {y})"}]}

    async def rightClick(coordinate: list[float]) -> dict[str, Any]:
        input_mod = requireComputerUseInput()
        x, y = coordinate[0], coordinate[1]
        await drainRunLoop(lambda: _do_click(input_mod, x, y, "right"))
        return {"content": [{"type": "text", "text": f"Right-clicked ({x}, {y})"}]}

    async def middleClick(coordinate: list[float]) -> dict[str, Any]:
        input_mod = requireComputerUseInput()
        x, y = coordinate[0], coordinate[1]
        await drainRunLoop(lambda: _do_click(input_mod, x, y, "middle"))
        return {"content": [{"type": "text", "text": f"Middle-clicked ({x}, {y})"}]}

    async def doubleClick(coordinate: list[float]) -> dict[str, Any]:
        input_mod = requireComputerUseInput()
        x, y = coordinate[0], coordinate[1]
        await drainRunLoop(lambda: _do_double_click(input_mod, x, y))
        return {"content": [{"type": "text", "text": f"Double-clicked ({x}, {y})"}]}

    async def tripleClick(coordinate: list[float]) -> dict[str, Any]:
        input_mod = requireComputerUseInput()
        x, y = coordinate[0], coordinate[1]
        await drainRunLoop(lambda: _do_triple_click(input_mod, x, y))
        return {"content": [{"type": "text", "text": f"Triple-clicked ({x}, {y})"}]}

    async def mouseMove(coordinate: list[float]) -> dict[str, Any]:
        input_mod = requireComputerUseInput()
        x, y = coordinate[0], coordinate[1]
        await drainRunLoop(lambda: moveAndSettle(input_mod, x, y))
        return {"content": [{"type": "text", "text": f"Moved to ({x}, {y})"}]}

    async def leftClickDrag(start_coordinate: list[float], coordinate: list[float]) -> dict[str, Any]:
        input_mod = requireComputerUseInput()
        sx, sy = start_coordinate[0], start_coordinate[1]
        ex, ey = coordinate[0], coordinate[1]
        await drainRunLoop(lambda: _do_drag(input_mod, sx, sy, ex, ey, get_mouse_animation_enabled()))
        return {"content": [{"type": "text", "text": f"Dragged ({sx}, {sy}) -> ({ex}, {ey})"}]}

    async def scroll(direction: str, amount: int, coordinate: list[float] | None = None) -> dict[str, Any]:
        input_mod = requireComputerUseInput()
        if coordinate:
            x, y = coordinate[0], coordinate[1]
            await drainRunLoop(lambda: _do_scroll_at(input_mod, x, y, direction, amount))
        else:
            await drainRunLoop(lambda: _do_scroll(input_mod, direction, amount))
        return {"content": [{"type": "text", "text": f"Scrolled {direction} x{amount}"}]}

    async def leftMouseDown(coordinate: list[float] | None = None) -> dict[str, Any]:
        input_mod = requireComputerUseInput()
        if coordinate:
            x, y = coordinate[0], coordinate[1]
            await drainRunLoop(lambda: _do_mouse_down(input_mod, x, y))
        else:
            await drainRunLoop(lambda: input_mod.mouseButton("left", "press"))
        return {"content": [{"type": "text", "text": "Mouse down"}]}

    async def leftMouseUp(coordinate: list[float] | None = None) -> dict[str, Any]:
        input_mod = requireComputerUseInput()
        if coordinate:
            x, y = coordinate[0], coordinate[1]
            await drainRunLoop(lambda: _do_mouse_up(input_mod, x, y))
        else:
            await drainRunLoop(lambda: input_mod.mouseButton("left", "release"))
        return {"content": [{"type": "text", "text": "Mouse up"}]}

    async def cursorPosition() -> dict[str, Any]:
        input_mod = requireComputerUseInput()
        pos = await drainRunLoop(lambda: input_mod.mouseLocation())
        return {"content": [{"type": "text", "text": f"Cursor at ({pos['x']}, {pos['y']})"}]}

    executor["leftClick"] = leftClick
    executor["rightClick"] = rightClick
    executor["middleClick"] = middleClick
    executor["doubleClick"] = doubleClick
    executor["tripleClick"] = tripleClick
    executor["mouseMove"] = mouseMove
    executor["leftClickDrag"] = leftClickDrag
    executor["scroll"] = scroll
    executor["leftMouseDown"] = leftMouseDown
    executor["leftMouseUp"] = leftMouseUp
    executor["cursorPosition"] = cursorPosition

    # ── Clipboard ────────────────────────────────────────────────────────

    async def readClipboard() -> dict[str, Any]:
        text = await readClipboardViaPbpaste()
        return {"content": [{"type": "text", "text": text}]}

    async def writeClipboard(text: str) -> dict[str, Any]:
        await writeClipboardViaPbcopy(text)
        return {"content": [{"type": "text", "text": "Clipboard written"}]}

    executor["readClipboard"] = readClipboard
    executor["writeClipboard"] = writeClipboard

    # ── Apps ─────────────────────────────────────────────────────────────

    async def listInstalledApps() -> list[dict[str, Any]]:
        return await drainRunLoop(lambda: cu.apps.listInstalled())

    async def openApplication(bundle_id: str) -> dict[str, Any]:
        await drainRunLoop(lambda: cu.apps.open(bundle_id))
        return {"content": [{"type": "text", "text": f"Opened {bundle_id}"}]}

    async def listGrantedApplications() -> dict[str, Any]:
        return {"content": [{"type": "text", "text": "Granted applications list"}]}

    async def requestAccess(apps: list[dict[str, Any]]) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": f"Access requested for {len(apps)} apps"}]}

    async def computerBatch(actions: list[dict[str, Any]]) -> dict[str, Any]:
        results = []
        for action in actions:
            name = action.get("name", "")
            args = action.get("args", {})
            method = executor.get(name)
            if callable(method):
                results.append(await method(**args))
        return {"content": [{"type": "text", "text": f"Executed {len(actions)} actions"}]}

    async def wait(duration: float) -> dict[str, Any]:
        await asyncio.sleep(duration)
        return {"content": [{"type": "text", "text": f"Waited {duration}s"}]}

    executor["listInstalledApps"] = listInstalledApps
    executor["openApplication"] = openApplication
    executor["listGrantedApplications"] = listGrantedApplications
    executor["requestAccess"] = requestAccess
    executor["computerBatch"] = computerBatch
    executor["wait"] = wait

    return executor


# ── Click helpers ────────────────────────────────────────────────────────

async def _do_click(input_mod: Any, x: float, y: float, button: str) -> None:
    await moveAndSettle(input_mod, x, y)
    await input_mod.mouseButton(button, "click")


async def _do_double_click(input_mod: Any, x: float, y: float) -> None:
    await moveAndSettle(input_mod, x, y)
    await input_mod.mouseButton("left", "click")
    await asyncio.sleep(0.05)
    await input_mod.mouseButton("left", "click")


async def _do_triple_click(input_mod: Any, x: float, y: float) -> None:
    await moveAndSettle(input_mod, x, y)
    for _ in range(3):
        await input_mod.mouseButton("left", "click")
        await asyncio.sleep(0.05)


async def _do_drag(input_mod: Any, sx: float, sy: float, ex: float, ey: float, animated: bool) -> None:
    await moveAndSettle(input_mod, sx, sy)
    await input_mod.mouseButton("left", "press")
    await animatedMove(input_mod, ex, ey, animated)
    await input_mod.mouseButton("left", "release")


async def _do_scroll(input_mod: Any, direction: str, amount: int) -> None:
    dx = amount if direction == "right" else (-amount if direction == "left" else 0)
    dy = amount if direction == "down" else (-amount if direction == "up" else 0)
    await input_mod.scroll(dx, dy)


async def _do_scroll_at(input_mod: Any, x: float, y: float, direction: str, amount: int) -> None:
    await moveAndSettle(input_mod, x, y)
    await _do_scroll(input_mod, direction, amount)


async def _do_mouse_down(input_mod: Any, x: float, y: float) -> None:
    await moveAndSettle(input_mod, x, y)
    await input_mod.mouseButton("left", "press")


async def _do_mouse_up(input_mod: Any, x: float, y: float) -> None:
    await moveAndSettle(input_mod, x, y)
    await input_mod.mouseButton("left", "release")


# ── Module-level exports ─────────────────────────────────────────────────

async def unhideComputerUseApps(bundleIds: list[str]) -> None:
    if not bundleIds:
        return
    cu = requireComputerUseSwift()
    await cu.apps.unhide(list(bundleIds))


compute_target_dims = computeTargetDims
read_clipboard_via_pbpaste = readClipboardViaPbpaste
write_clipboard_via_pbcopy = writeClipboardViaPbcopy
is_bare_escape = isBareEscape
move_and_settle = moveAndSettle
release_pressed = releasePressed
with_modifiers = withModifiers
type_via_clipboard = typeViaClipboard
animated_move = animatedMove
create_cli_executor = createCliExecutor
unhide_computer_use_apps = unhideComputerUseApps

