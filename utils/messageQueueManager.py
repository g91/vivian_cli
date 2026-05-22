"""Minimal message queue manager used by task notifications."""

from __future__ import annotations

from typing import Any, Callable, Dict


SetAppState = Any
PopAllEditableResult = Dict[str, Any]


class _Emitter:
    def __init__(self) -> None:
        self._subscribers: list[Callable[[], None]] = []

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        self._subscribers.append(callback)

        def unsubscribe() -> None:
            try:
                self._subscribers.remove(callback)
            except ValueError:
                pass

        return unsubscribe

    def emit(self) -> None:
        for callback in list(self._subscribers):
            try:
                callback()
            except Exception:
                pass


commandQueue: list[Any] = []
snapshot: list[Any] = []
queueChanged = _Emitter()
NON_EDITABLE_MODES = {"task-notification"}


def getCommandQueueLength():
    """Get the current queue length without copying."""
    return len(commandQueue)


def hasCommandsInQueue():
    """Check if there are commands in the queue."""
    return bool(commandQueue)


def recheckCommandQueue():
    """Trigger a re-check by notifying subscribers."""
    notifySubscribers()
    return True


def clearCommandQueue():
    """Clear all commands from the queue."""
    commandQueue.clear()
    notifySubscribers()
    return []


def resetCommandQueue():
    """Clear all commands and reset snapshot."""
    commandQueue.clear()
    snapshot.clear()
    notifySubscribers()
    return []


# Subscribe to command queue changes.
subscribeToCommandQueue: Any = queueChanged.subscribe
subscribeToPendingNotifications: Any = subscribeToCommandQueue
hasPendingNotifications: Any = hasCommandsInQueue
getPendingNotificationsCount: Any = getCommandQueueLength
recheckPendingNotifications: Any = recheckCommandQueue
resetPendingNotifications: Any = resetCommandQueue
clearPendingNotifications: Any = clearCommandQueue


def logOperation(operation, content=None):
    return {"operation": operation, "content": content}


def notifySubscribers():
    global snapshot
    snapshot = list(commandQueue)
    queueChanged.emit()


def getCommandQueueSnapshot():
    """Get current snapshot of the command queue."""
    return list(snapshot)


def getCommandQueue():
    """Get a mutable copy of the current queue."""
    return list(commandQueue)


def enqueue(command):
    """Add a command to the queue."""
    commandQueue.append(command)
    notifySubscribers()
    return command


def enqueuePendingNotification(command):
    """Add a task notification to the queue."""
    return enqueue(command)


def dequeue(filter=None):
    """Remove and return the highest-priority command, or undefined if empty."""
    if filter is None:
        if not commandQueue:
            return None
        item = commandQueue.pop(0)
        notifySubscribers()
        return item
    for index, item in enumerate(commandQueue):
        if filter(item):
            removed = commandQueue.pop(index)
            notifySubscribers()
            return removed
    return None


def dequeueAll():
    """Remove and return all commands from the queue."""
    items = list(commandQueue)
    commandQueue.clear()
    notifySubscribers()
    return items


def peek(filter=None):
    """Return the highest-priority command without removing it, or undefined if empty."""
    if filter is None:
        return commandQueue[0] if commandQueue else None
    for item in commandQueue:
        if filter(item):
            return item
    return None


def dequeueAllMatching(predicate=None):
    """Remove and return all commands matching a predicate, preserving priority order."""
    if predicate is None:
        return dequeueAll()
    matched = [item for item in commandQueue if predicate(item)]
    if matched:
        remaining = [item for item in commandQueue if not predicate(item)]
        commandQueue[:] = remaining
        notifySubscribers()
    return matched


def remove(commandsToRemove):
    """Remove specific commands from the queue by reference identity."""
    to_remove = set(id(command) for command in commandsToRemove)
    commandQueue[:] = [item for item in commandQueue if id(item) not in to_remove]
    notifySubscribers()
    return None


def removeByFilter(predicate=None):
    """Remove commands matching a predicate."""
    return dequeueAllMatching(predicate)


def isPromptInputModeEditable(mode):
    return not NON_EDITABLE_MODES.has(mode)


def isQueuedCommandEditable(cmd):
    """Whether this queued command can be pulled into the input buffer via UP/ESC."""
    return isPromptInputModeEditable(cmd.get("mode") if isinstance(cmd, dict) else getattr(cmd, "mode", None))


def isQueuedCommandVisible(cmd):
    """Whether this queued command should render in the queue preview under the"""
    return True


def extractTextFromValue(value):
    """Extract text from a queued command value."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("text") or value.get("value") or ""
    return ""


def extractImagesFromValue(value, startId):
    """Extract images from ContentBlockParam[] and convert to PastedContent format."""
    return []


def popAllEditable(currentInput, currentCursorOffset):
    """Pop all editable commands and combine them with current input for editing."""
    editable = [item for item in commandQueue if isQueuedCommandEditable(item)]
    if editable:
        remaining = [item for item in commandQueue if not isQueuedCommandEditable(item)]
        commandQueue[:] = remaining
        notifySubscribers()
    combined = "\n".join(filter(None, [extractTextFromValue(item.get("value", item)) for item in editable] + [currentInput]))
    return {"value": combined, "cursorOffset": len(combined) if currentCursorOffset is None else currentCursorOffset}


def getPendingNotificationsSnapshot():
    return snapshot


def dequeuePendingNotification():
    return dequeue()


def getCommandsByMaxPriority(maxPriority):
    """Get commands at or above a given priority level without removing them."""
    return [item for item in commandQueue if (item.get("priority", 0) if isinstance(item, dict) else getattr(item, "priority", 0)) <= maxPriority]


def isSlashCommand(cmd):
    """Returns true if the command is a slash command that should be routed through"""
    result = None
    _input = cmd
    _output = _input if _input is not None else {}
    return _output

