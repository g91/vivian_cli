"""Todo item types — mirrors src/utils/todo/types.ts"""
from __future__ import annotations

from typing import Literal

TodoStatus = Literal["pending", "in_progress", "completed"]


class TodoItem:
    """A single todo item."""

    def __init__(self, content: str, status: TodoStatus, active_form: str) -> None:
        if not content:
            raise ValueError("content cannot be empty")
        if not active_form:
            raise ValueError("active_form cannot be empty")
        self.content = content
        self.status = status
        self.active_form = active_form

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "status": self.status,
            "activeForm": self.active_form,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TodoItem":
        return cls(
            content=d["content"],
            status=d["status"],
            active_form=d["activeForm"],
        )


TodoList = list[TodoItem]
