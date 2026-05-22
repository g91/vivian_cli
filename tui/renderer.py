"""Rich-based TUI — replicates the exact look of the original vivian Code GUI.

Mirrors the Ink/React component tree:
- StatusLine at the bottom (model, cost, permission mode, context %)
- Message display area (user=blue, assistant=white, system=dim)
- PromptInput with > character and model badge
- SpinnerWithVerb animation
- CompanionSprite (buddy) on the right
"""

from __future__ import annotations

import asyncio
import time
import random
from typing import Optional, Callable

from rich.console import Console, RenderableType
from rich.text import Text
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich.style import Style
from rich.align import Align
from rich.box import Box, ROUNDED, SIMPLE

from .theme import Theme, get_theme, theme_to_rich_style, ThemeName
from .buddy import BuddyManager
from ..types import Message, AppState, PermissionMode
from ..cost_tracker import CostTracker
from ..utils.format import format_duration, format_cost, format_number


# ── StatusLine ─────────────────────────────────────────────

def render_statusline(
    model: str,
    permission_mode: PermissionMode,
    cost_tracker: CostTracker,
    context_used_pct: float = 0.0,
    vim_enabled: bool = False,
    plan_mode: bool = False,
    fast_mode: bool = False,
    width: int = 80,
) -> Text:
    """Render the bottom statusline bar — mirrors StatusLine.tsx."""
    theme = get_theme("dark")
    styles = theme_to_rich_style(theme)

    # Model badge
    model_text = Text(" ", style=styles["statusline.model"])
    model_text.append(f" {model} ", style=styles["statusline.model"])

    # Permission mode badge
    mode_color = {
        PermissionMode.DEFAULT: "inactive",
        PermissionMode.ACCEPT_EDITS: "success",
        PermissionMode.BYPASS_PERMISSIONS: "warning",
        PermissionMode.PLAN: "plan",
    }.get(permission_mode, "inactive")

    mode_label = {
        PermissionMode.DEFAULT: "DEFAULT",
        PermissionMode.ACCEPT_EDITS: "ACCEPT EDITS",
        PermissionMode.BYPASS_PERMISSIONS: "BYPASS",
        PermissionMode.PLAN: "PLAN MODE",
    }.get(permission_mode, "DEFAULT")

    mode_text = Text(f" {mode_label} ", style=styles.get(mode_color, ""))

    # Cost
    cost_str = format_cost(cost_tracker.total_cost_usd)
    cost_text = Text(f" ${cost_str} ", style=styles["statusline.cost"])

    # Context bar
    bar_width = 20
    filled = int(bar_width * min(context_used_pct / 100, 1.0))
    bar = "█" * filled + "░" * (bar_width - filled)
    ctx_text = Text(f" {bar} {context_used_pct:.0f}% ", style=styles["statusline.context"])

    # Mode indicators
    indicators = []
    if vim_enabled:
        indicators.append(Text(" VIM ", style=styles["agent.purple"]))
    if plan_mode:
        indicators.append(Text(" PLAN ", style=styles["plan"]))
    if fast_mode:
        indicators.append(Text(" FAST ", style=styles["fast"]))

    # Assemble
    result = Text()
    result.append(model_text)
    result.append(" ")
    result.append(mode_text)
    result.append(" ")
    result.append(cost_text)
    result.append(" " * 4)
    result.append(ctx_text)

    for ind in indicators:
        result.append(" ")
        result.append(ind)

    # Right-align the whole thing
    return result


# ── Message Rendering ──────────────────────────────────────

def render_message(msg: Message, theme: Theme, width: int = 80) -> RenderableType:
    """Render a single message — mirrors Message.tsx."""
    styles = theme_to_rich_style(theme)

    if msg.role == "user":
        return Panel(
            Text(msg.content or "", style=styles["user"]),
            border_style=styles["border"],
            box=SIMPLE,
            title="You",
            title_align="left",
            padding=(0, 1),
        )
    elif msg.role == "assistant":
        if msg.content:
            return Text(msg.content, style=styles["assistant"])
        elif msg.tool_calls:
            lines = Text()
            for tc in msg.tool_calls:
                name = tc.get("function", {}).get("name", "unknown")
                lines.append(f"  ⚙ {name}\n", style=styles["inactive"])
            return lines
        return Text("")
    elif msg.role == "system":
        return Text(f"  {msg.content}", style=styles["system"])
    elif msg.role == "tool":
        content = msg.content or ""
        if len(content) > 500:
            content = content[:500] + "..."
        return Panel(
            Text(content, style=styles["inactive"]),
            border_style=styles["bash.border"],
            box=SIMPLE,
            title=f"Tool: {msg.tool_call_id or ''}",
            title_align="left",
            padding=(0, 1),
        )
    return Text("")


def render_messages(
    messages: list[Message],
    theme: Theme,
    width: int = 80,
    max_messages: int = 20,
) -> RenderableType:
    """Render the message history — mirrors Messages.tsx."""
    # Show last N messages
    visible = messages[-max_messages:]

    result = Text()
    for i, msg in enumerate(visible):
        if i > 0:
            result.append("\n\n")
        rendered = render_message(msg, theme, width)
        if isinstance(rendered, Text):
            result.append(rendered)
        else:
            result.append("\n")
            # For Panel, we'd need a different approach — use Text for now
            if isinstance(rendered, Panel):
                result.append(rendered.renderable)  # type: ignore

    return result


# ── Spinner ────────────────────────────────────────────────

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
SPINNER_VERBS = [
    "thinking", "analyzing", "processing", "generating",
    "reading", "writing", "searching", "executing",
    "computing", "compiling", "building", "testing",
]


def render_spinner(
    frame_idx: int,
    mode: str = "thinking",
    message: Optional[str] = None,
    theme: Theme = get_theme("dark"),
) -> Text:
    """Render the animated spinner — mirrors Spinner.tsx."""
    styles = theme_to_rich_style(theme)
    frame = SPINNER_FRAMES[frame_idx % len(SPINNER_FRAMES)]

    result = Text()
    result.append(f"{frame} ", style=styles["vivian"])

    if message:
        result.append(message, style=styles["vivian"])
    else:
        verb = SPINNER_VERBS[frame_idx % len(SPINNER_VERBS)]
        result.append(f"{verb}...", style=styles["vivian"])

    return result


# ── Prompt Input ───────────────────────────────────────────

def render_prompt_input(
    text: str = "",
    model: str = "",
    vim_mode: str = "",
    placeholder: str = "Type a message...",
    theme: Theme = get_theme("dark"),
    focused: bool = True,
) -> RenderableType:
    """Render the prompt input area — mirrors PromptInput.tsx."""
    styles = theme_to_rich_style(theme)

    border_style = styles["border.focused"] if focused else styles["border"]

    # Build the prompt line
    prompt_line = Text()

    # $> prompt character
    prompt_line.append("$> ", style=styles["prompt"])

    # Input text or placeholder
    if text:
        prompt_line.append(text, style=styles["text"])
    else:
        prompt_line.append(placeholder, style=styles["inactive"])

    # VIM mode indicator
    if vim_mode:
        prompt_line.append(f" [{vim_mode}]", style=styles["agent.purple"])

    return Panel(
        prompt_line,
        border_style=border_style,
        box=ROUNDED,
        padding=(0, 1),
    )


# ── Header ─────────────────────────────────────────────────

def render_header(
    model: str,
    base_url: str,
    session_id: str = "",
    theme: Theme = get_theme("dark"),
) -> RenderableType:
    """Render the top header bar."""
    styles = theme_to_rich_style(theme)

    header = Text()
    header.append("╭", style=styles["border"])
    header.append(" Vivian CLI ", style=styles["vivian"])
    header.append("─" * 40, style=styles["border"])
    header.append("╮", style=styles["border"])
    header.append("\n")
    header.append("│", style=styles["border"])
    header.append(f"  Model: {model}", style=styles["text"])
    header.append(" " * 20)
    header.append(f"API: {base_url}", style=styles["inactive"])
    header.append(" │", style=styles["border"])
    header.append("\n")
    header.append("╰", style=styles["border"])
    header.append("─" * 58, style=styles["border"])
    header.append("╯", style=styles["border"])

    return header


# ── Full Layout ────────────────────────────────────────────

def build_layout(
    messages: list[Message],
    prompt_text: str,
    model: str,
    permission_mode: PermissionMode,
    cost_tracker: CostTracker,
    vim_enabled: bool = False,
    plan_mode: bool = False,
    fast_mode: bool = False,
    is_streaming: bool = False,
    spinner_frame: int = 0,
    spinner_message: Optional[str] = None,
    buddy: Optional[BuddyManager] = None,
    width: int = 80,
    height: int = 24,
    base_url: str = "",
    session_id: str = "",
) -> Layout:
    """Build the full terminal layout."""
    theme = get_theme("dark")

    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="statusline", size=1),
    )

    # Header
    layout["header"].update(render_header(model, base_url, session_id, theme))

    # Body: messages + prompt
    body = Layout()
    body.split(
        Layout(name="messages"),
        Layout(name="prompt", size=3),
    )

    # Messages
    msg_render = render_messages(messages, theme, width)
    body["messages"].update(msg_render)

    # Prompt
    prompt_render = render_prompt_input(
        text=prompt_text,
        model=model,
        vim_mode="NORMAL" if vim_enabled else "",
        theme=theme,
    )
    body["prompt"].update(prompt_render)

    layout["body"].update(body)

    # Statusline
    statusline = render_statusline(
        model=model,
        permission_mode=permission_mode,
        cost_tracker=cost_tracker,
        vim_enabled=vim_enabled,
        plan_mode=plan_mode,
        fast_mode=fast_mode,
        width=width,
    )
    layout["statusline"].update(Align.right(statusline))

    return layout
