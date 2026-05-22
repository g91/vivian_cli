"""VIM mode — mirrors src/vim/.

Implements VIM-like modal editing for the input buffer.
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable


class VimMode(str, Enum):
    NORMAL = "normal"
    INSERT = "insert"
    VISUAL = "visual"
    VISUAL_LINE = "visual-line"
    OPERATOR_PENDING = "operator-pending"
    COMMAND = "command"


@dataclass
class VimState:
    mode: VimMode = VimMode.NORMAL
    register: str = '"'
    operator: Optional[str] = None
    count: Optional[int] = None
    last_change: Optional[str] = None
    cursor_pos: int = 0
    visual_start: Optional[int] = None


class VimEngine:
    """VIM modal editing engine for text input."""

    def __init__(self):
        self.state = VimState()
        self._text: str = ""
        self._on_change: Optional[Callable[[str, int], None]] = None

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str):
        self._text = value

    @property
    def mode(self) -> VimMode:
        return self.state.mode

    def set_on_change(self, callback: Callable[[str, int], None]):
        self._on_change = callback

    def _notify(self):
        if self._on_change:
            self._on_change(self._text, self.state.cursor_pos)

    # ── Mode Transitions ───────────────────────────────────

    def enter_insert(self, pos: Optional[int] = None):
        self.state.mode = VimMode.INSERT
        if pos is not None:
            self.state.cursor_pos = pos

    def enter_normal(self):
        self.state.mode = VimMode.NORMAL
        self.state.operator = None
        self.state.count = None
        self.state.visual_start = None

    def enter_visual(self):
        self.state.mode = VimMode.VISUAL
        self.state.visual_start = self.state.cursor_pos

    def enter_visual_line(self):
        self.state.mode = VimMode.VISUAL_LINE
        self.state.visual_start = self.state.cursor_pos

    # ── Motions ────────────────────────────────────────────

    def move_left(self, count: int = 1):
        self.state.cursor_pos = max(0, self.state.cursor_pos - count)

    def move_right(self, count: int = 1):
        self.state.cursor_pos = min(len(self._text), self.state.cursor_pos + count)

    def move_word_forward(self, count: int = 1):
        for _ in range(count):
            # Skip current word
            while self.state.cursor_pos < len(self._text) and self._text[self.state.cursor_pos].isalnum():
                self.state.cursor_pos += 1
            # Skip whitespace
            while self.state.cursor_pos < len(self._text) and not self._text[self.state.cursor_pos].isalnum():
                self.state.cursor_pos += 1

    def move_word_backward(self, count: int = 1):
        for _ in range(count):
            # Skip whitespace
            while self.state.cursor_pos > 0 and not self._text[self.state.cursor_pos - 1].isalnum():
                self.state.cursor_pos -= 1
            # Skip word
            while self.state.cursor_pos > 0 and self._text[self.state.cursor_pos - 1].isalnum():
                self.state.cursor_pos -= 1

    def move_to_start(self):
        self.state.cursor_pos = 0

    def move_to_end(self):
        self.state.cursor_pos = len(self._text)

    def move_to_line_start(self):
        # Find start of current line
        pos = self.state.cursor_pos
        while pos > 0 and self._text[pos - 1] != '\n':
            pos -= 1
        self.state.cursor_pos = pos

    def move_to_line_end(self):
        # Find end of current line
        pos = self.state.cursor_pos
        while pos < len(self._text) and self._text[pos] != '\n':
            pos += 1
        self.state.cursor_pos = pos

    # ── Operators ──────────────────────────────────────────

    def delete_char(self, count: int = 1):
        end = min(len(self._text), self.state.cursor_pos + count)
        deleted = self._text[self.state.cursor_pos:end]
        self._text = self._text[:self.state.cursor_pos] + self._text[end:]
        self.state.last_change = f"x{deleted}"
        self._notify()

    def delete_backward(self, count: int = 1):
        start = max(0, self.state.cursor_pos - count)
        deleted = self._text[start:self.state.cursor_pos]
        self._text = self._text[:start] + self._text[self.state.cursor_pos:]
        self.state.cursor_pos = start
        self.state.last_change = f"X{deleted}"
        self._notify()

    def delete_line(self):
        line_start = self.state.cursor_pos
        while line_start > 0 and self._text[line_start - 1] != '\n':
            line_start -= 1
        line_end = self.state.cursor_pos
        while line_end < len(self._text) and self._text[line_end] != '\n':
            line_end += 1
        # Include newline if present
        if line_end < len(self._text):
            line_end += 1

        deleted = self._text[line_start:line_end]
        self._text = self._text[:line_start] + self._text[line_end:]
        self.state.cursor_pos = line_start
        self.state.last_change = f"dd{deleted}"
        self._notify()

    def delete_to_end(self):
        deleted = self._text[self.state.cursor_pos:]
        self._text = self._text[:self.state.cursor_pos]
        self.state.last_change = f"D{deleted}"
        self._notify()

    def change_to_end(self):
        deleted = self._text[self.state.cursor_pos:]
        self._text = self._text[:self.state.cursor_pos]
        self.state.last_change = f"C{deleted}"
        self.enter_insert()
        self._notify()

    def change_line(self):
        self.delete_line()
        self.enter_insert()

    def paste_after(self):
        if self.state.last_change:
            # Extract content from last change (strip operator prefix)
            content = self.state.last_change
            # Remove operator prefix (first 1-2 chars)
            if content.startswith(('x', 'X', 'D', 'C')):
                content = content[1:]
            elif content.startswith('dd'):
                content = content[2:]

            pos = min(len(self._text), self.state.cursor_pos + 1)
            self._text = self._text[:pos] + content + self._text[pos:]
            self.state.cursor_pos = pos + len(content)
            self._notify()

    def paste_before(self):
        if self.state.last_change:
            content = self.state.last_change
            if content.startswith(('x', 'X', 'D', 'C')):
                content = content[1:]
            elif content.startswith('dd'):
                content = content[2:]

            self._text = self._text[:self.state.cursor_pos] + content + self._text[self.state.cursor_pos:]
            self.state.cursor_pos += len(content)
            self._notify()

    def insert_at_cursor(self, char: str):
        self._text = self._text[:self.state.cursor_pos] + char + self._text[self.state.cursor_pos:]
        self.state.cursor_pos += 1
        self._notify()

    def insert_newline(self):
        self._text = self._text[:self.state.cursor_pos] + '\n' + self._text[self.state.cursor_pos:]
        self.state.cursor_pos += 1
        self._notify()

    # ── Key Handler ────────────────────────────────────────

    def handle_key(self, key: str) -> bool:
        """Handle a keypress. Returns True if key was consumed."""
        if self.state.mode == VimMode.INSERT:
            return self._handle_insert(key)
        elif self.state.mode == VimMode.NORMAL:
            return self._handle_normal(key)
        elif self.state.mode in (VimMode.VISUAL, VimMode.VISUAL_LINE):
            return self._handle_visual(key)
        return False

    def _handle_insert(self, key: str) -> bool:
        if key == '\x1b':  # Escape
            self.enter_normal()
            self.state.cursor_pos = max(0, self.state.cursor_pos - 1)
            return True
        elif key == '\x7f' or key == '\b':  # Backspace
            self.delete_backward()
            return True
        elif key == '\r' or key == '\n':  # Enter
            self.insert_newline()
            return True
        elif len(key) == 1 and key.isprintable():
            self.insert_at_cursor(key)
            return True
        return False

    def _handle_normal(self, key: str) -> bool:
        # Count prefix
        if key.isdigit() and key != '0':
            if self.state.count is None:
                self.state.count = 0
            self.state.count = self.state.count * 10 + int(key)
            return True

        count = self.state.count or 1

        if key == 'i':
            self.enter_insert()
            return True
        elif key == 'a':
            self.state.cursor_pos = min(len(self._text), self.state.cursor_pos + 1)
            self.enter_insert()
            return True
        elif key == 'I':
            self.move_to_line_start()
            self.enter_insert()
            return True
        elif key == 'A':
            self.move_to_line_end()
            self.enter_insert()
            return True
        elif key == 'o':
            self.move_to_line_end()
            self.insert_newline()
            self.enter_insert()
            return True
        elif key == 'O':
            self.move_to_line_start()
            self._text = self._text[:self.state.cursor_pos] + '\n' + self._text[self.state.cursor_pos:]
            self.enter_insert()
            return True
        elif key == 'h':
            self.move_left(count)
            return True
        elif key == 'l':
            self.move_right(count)
            return True
        elif key == 'w':
            self.move_word_forward(count)
            return True
        elif key == 'b':
            self.move_word_backward(count)
            return True
        elif key == '0':
            self.move_to_line_start()
            return True
        elif key == '$':
            self.move_to_line_end()
            return True
        elif key == 'x':
            self.delete_char(count)
            return True
        elif key == 'X':
            self.delete_backward(count)
            return True
        elif key == 'd' and self.state.operator is None:
            self.state.operator = 'd'
            self.state.mode = VimMode.OPERATOR_PENDING
            return True
        elif key == 'd' and self.state.operator == 'd':
            self.delete_line()
            self.enter_normal()
            return True
        elif key == 'D':
            self.delete_to_end()
            return True
        elif key == 'c' and self.state.operator is None:
            self.state.operator = 'c'
            self.state.mode = VimMode.OPERATOR_PENDING
            return True
        elif key == 'c' and self.state.operator == 'c':
            self.change_line()
            return True
        elif key == 'C':
            self.change_to_end()
            return True
        elif key == 'p':
            self.paste_after()
            return True
        elif key == 'P':
            self.paste_before()
            return True
        elif key == 'v':
            self.enter_visual()
            return True
        elif key == 'V':
            self.enter_visual_line()
            return True
        elif key == '\x1b':  # Escape
            self.enter_normal()
            return True

        # Operator-pending motions
        if self.state.mode == VimMode.OPERATOR_PENDING:
            if key == 'w':
                self.move_word_forward(count)
                if self.state.operator == 'd':
                    # Delete from original position to new position
                    pass
                self.enter_normal()
                return True

        self.state.count = None
        return False

    def _handle_visual(self, key: str) -> bool:
        if key == '\x1b':  # Escape
            self.enter_normal()
            return True
        elif key == 'y':
            # Yank selection
            start = min(self.state.visual_start or 0, self.state.cursor_pos)
            end = max(self.state.visual_start or 0, self.state.cursor_pos)
            self.state.last_change = self._text[start:end + 1]
            self.enter_normal()
            return True
        elif key == 'd':
            # Delete selection
            start = min(self.state.visual_start or 0, self.state.cursor_pos)
            end = max(self.state.visual_start or 0, self.state.cursor_pos)
            self.state.last_change = self._text[start:end + 1]
            self._text = self._text[:start] + self._text[end + 1:]
            self.state.cursor_pos = start
            self.enter_normal()
            self._notify()
            return True
        elif key == 'h':
            self.move_left()
            return True
        elif key == 'l':
            self.move_right()
            return True
        return False
