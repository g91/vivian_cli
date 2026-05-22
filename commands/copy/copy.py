"""copy command — mirrors src/commands/copy/copy.tsx.

Copy the last assistant response to clipboard.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


COPY_DIR = Path(tempfile.gettempdir()) / "vivian"
RESPONSE_FILENAME = "response.md"
MAX_LOOKBACK = 20


def _message_field(message: object, field: str, default: str = "") -> str:
    if hasattr(message, field):
        value = getattr(message, field)
        return value if isinstance(value, str) else default
    if isinstance(message, dict):
        value = message.get(field, default)
        return value if isinstance(value, str) else default
    return default


def collectRecentAssistantTexts(messages: list[object]) -> list[str]:
    """Return recent assistant texts newest-first."""
    texts: list[str] = []
    for message in reversed(messages):
        if len(texts) >= MAX_LOOKBACK:
            break
        if _message_field(message, "role") != "assistant":
            continue
        content = _message_field(message, "content").strip()
        if content:
            texts.append(content)
    return texts


def _write_to_file(text: str, filename: str = RESPONSE_FILENAME) -> Path:
    COPY_DIR.mkdir(parents=True, exist_ok=True)
    file_path = COPY_DIR / filename
    file_path.write_text(text, encoding="utf-8")
    return file_path


def _clipboard_available() -> bool:
    if os.name != "posix":
        return True
    if os.environ.get("WAYLAND_DISPLAY"):
        return True
    display = os.environ.get("DISPLAY")
    if not display:
        return False
    try:
        probe = subprocess.run(
            ["xdpyinfo"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return probe.returncode == 0
    except Exception:
        return False


def _copy_to_clipboard(text: str) -> bool:
    if not _clipboard_available():
        return False
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except Exception:
        return False


def copyLastResponse(messages: list[object], age: int = 0) -> str:
    """Copy a recent assistant response and always write a temp-file fallback."""
    texts = collectRecentAssistantTexts(messages)
    if not texts:
        return "No assistant message to copy"
    if age >= len(texts):
        noun = "message" if len(texts) == 1 else "messages"
        return f"Only {len(texts)} assistant {noun} available to copy"

    text = texts[age]
    line_count = text.count("\n") + 1
    char_count = len(text)
    file_path = _write_to_file(text)

    if _copy_to_clipboard(text):
        return (
            f"Copied to clipboard ({char_count} characters, {line_count} lines)\n"
            f"Also written to {file_path}"
        )

    return (
        f"Written to {file_path} ({char_count} characters, {line_count} lines)\n"
        "Clipboard unavailable."
    )


async def call(args: str, context: CommandContext) -> TextResult:
    """Copy last response."""
    from ...types.command import TextResult

    arg = (args or "").strip()
    age = 0
    if arg:
        try:
            value = int(arg)
        except ValueError:
            return TextResult(f"Usage: /copy [N] where N is 1 (latest), 2, 3, ... Got: {arg}")
        if value < 1:
            return TextResult(f"Usage: /copy [N] where N is 1 (latest), 2, 3, ... Got: {arg}")
        age = value - 1

    try:
        qe = getattr(context, "query_engine", None)
        if qe:
            msgs = getattr(qe, "messages", []) or []
            result = copyLastResponse(msgs, age)
            return TextResult(result)
    except Exception:
        pass
    return TextResult("No assistant message to copy")


copy_last_response = copyLastResponse
collect_recent_assistant_texts = collectRecentAssistantTexts
