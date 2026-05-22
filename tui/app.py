"""Main TUI application — prompt_toolkit input + Rich display.

Replicates the exact look and feel of the original vivian Code GUI:
- Dark theme with amber/orange vivian brand color
- Statusline at bottom with model, cost, permission mode, context %
- Message display with user (blue) and assistant (white) styling
- > prompt with model badge
- Animated spinner during streaming
- Buddy companion (optional)
- VIM mode indicator
"""

from __future__ import annotations

import asyncio
import sys
from typing import Optional, Callable, AsyncGenerator, Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED

from .theme import get_theme, theme_to_rich_style
from .buddy import BuddyManager
from ..utils.debug_log import dlog as _dlog
from ..types import Message, PermissionMode
from ..cost_tracker import CostTracker
from ..utils.format import format_cost

# Native yoga layout (optional — graceful fallback)
try:
    from ..native.yoga_layout import Node as YogaNode, FlexDirection, Justify
    _HAS_YOGA = True
except ImportError:
    _HAS_YOGA = False

SPINNER_CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
SPINNER_VERBS = ["Thinking", "Processing", "Analyzing", "Working", "Computing"]


class VivianTUI:
    """Interactive TUI using prompt_toolkit for input + Rich for display."""

    def __init__(
        self,
        model: str = "qwen3.6:latest",
        base_url: str = "https://api-vivian.d0a.net",
        permission_mode: PermissionMode = PermissionMode.DEFAULT,
        cost_tracker: Optional[CostTracker] = None,
        vim_enabled: bool = False,
        buddy_enabled: bool = True,
    ):
        self.console = Console()
        self.model = model
        self.base_url = base_url
        self.permission_mode = permission_mode
        self.cost_tracker = cost_tracker or CostTracker()
        self.vim_enabled = vim_enabled
        self.buddy_enabled = buddy_enabled

        # Theme
        self.theme = get_theme("dark")
        self.styles = theme_to_rich_style(self.theme)

        # Buddy
        self.buddy = BuddyManager(enabled=buddy_enabled)

        # State
        self.messages: list[Message] = []
        self.is_streaming = False
        self.session_id = ""
        self.plan_mode = False
        self.fast_mode = False
        self._running = False

        # Callbacks
        self._on_submit: Optional[Callable] = None
        self._on_interrupt: Optional[Callable] = None

    # ── Callbacks ─────────────────────────────────────────

    def set_on_submit(self, callback: Callable) -> None:
        self._on_submit = callback

    def set_on_interrupt(self, callback: Callable) -> None:
        self._on_interrupt = callback

    # ── Public API (cli_main.py compatibility) ────────────

    def add_message(self, msg: Message) -> None:
        """Add and immediately print a message."""
        self.messages.append(msg)
        self._print_message(msg)

    def set_streaming(self, active: bool) -> None:
        """Set streaming state (used by legacy _process_tui_query)."""
        self.is_streaming = active

    def append_stream(self, text: str) -> None:
        """Write streaming text directly to stdout (legacy compat)."""
        sys.stdout.write(text)
        sys.stdout.flush()

    def add_tool_start(self, tool_name: str) -> None:
        """Show a live 'calling tool…' indicator as the tool name arrives."""
        sys.stdout.write(f"\n  ⚙ {tool_name} …")
        sys.stdout.flush()

    def add_tool_success(self, tool_name: str, result: Any) -> None:
        """Show a brief success line after a tool completes."""
        try:
            import json
            summary = json.dumps(result, default=str)
            if len(summary) > 100:
                summary = summary[:97] + "..."
        except Exception:
            summary = str(result)[:100]
        self.console.print(f"  [green]✔[/green] [dim]{tool_name}:[/dim] [dim]{summary}[/dim]")

    def add_tool_error(self, tool_name: str, error: str) -> None:
        """Show an error line after a tool fails."""
        self.console.print(f"  [red]✗[/red] [dim]{tool_name}:[/dim] [red]{error}[/red]")

    def set_prompt(self, text: str) -> None:
        pass  # no-op in prompt_toolkit design

    def set_spinner(self, frame: int, message: Optional[str] = None) -> None:
        pass  # spinner is managed internally during _stream_query

    def set_model(self, model: str) -> None:
        self.model = model

    def set_permission_mode(self, mode: PermissionMode) -> None:
        self.permission_mode = mode

    def toggle_vim(self) -> None:
        self.vim_enabled = not self.vim_enabled

    def toggle_plan(self) -> None:
        self.plan_mode = not self.plan_mode

    def toggle_fast(self) -> None:
        self.fast_mode = not self.fast_mode

    def clear_messages(self) -> None:
        self.messages.clear()
        self.console.clear()

    def stop(self) -> None:
        self._running = False

    # ── Display helpers ────────────────────────────────────

    def _print_message(self, msg: Message) -> None:
        """Print a single message to the Rich console."""
        if msg.role == "user":
            self.console.print(f"\n[bold #93C5FD]▌[/] [#93C5FD]{msg.content or ''}[/]\n")
        elif msg.role == "assistant" and msg.content:
            self.console.print(f"[#F9FAFB]{msg.content}[/]\n")
        elif msg.role == "system" and msg.content:
            self.console.print(f"[dim]{msg.content}[/dim]")
        elif msg.role == "tool" and msg.content:
            self.console.print(f"[dim]  ⚙ {msg.content[:200]}[/dim]")

    @property
    def _short_model(self) -> str:
        """Abbreviated model name for display (strips owner prefix, truncates)."""
        name = self.model or "unknown"
        if "/" in name:
            name = name.rsplit("/", 1)[-1]
        return (name[:28] + "\u2026") if len(name) > 29 else name

    def _print_welcome(self) -> None:
        """Print the welcome header."""
        layout = self.compute_panel_layout()
        main_width = layout["main"]

        # Hostname only from URL
        api_host = self.base_url.rstrip("/")
        for prefix in ("https://", "http://"):
            if api_host.startswith(prefix):
                api_host = api_host[len(prefix):]
                break

        header = Text()
        header.append("Vivian CLI", style="bold #D97706")
        header.append("  │  ", style="#374151")
        header.append(self._short_model, style="#9CA3AF")
        header.append("  │  ", style="#374151")
        header.append(api_host, style="dim #6B7280 underline")

        self.console.print()
        self.console.print(Panel(
            header,
            border_style="#374151",
            box=ROUNDED,
            expand=False,
            width=min(main_width, self.console.width),
            padding=(0, 2),
        ))
        self.console.print(
            "[dim]  (\u3065\u25e1\ufe0f\u25c1\ufe0f\u25e1)\u3065  "
            "Type a message or [bold #D97706]/help[/bold #D97706] for commands.  "
            "Ctrl+C to interrupt, Ctrl+D to exit.[/dim]"
        )
        self.console.print()

    # ── prompt_toolkit helpers ─────────────────────────────

    def _get_prompt_tokens(self) -> Any:
        """Build the styled prompt prefix — just $> so the cursor stays compact."""
        from prompt_toolkit.formatted_text import FormattedText
        tokens: list[tuple[str, str]] = [
            ("class:prompt-gt", "$> "),
        ]
        if self.vim_enabled:
            tokens.append(("class:prompt-vim", "[N] "))
        return FormattedText(tokens)

    def _get_toolbar(self) -> Any:
        """Build the bottom toolbar showing the statusline."""
        from prompt_toolkit.formatted_text import FormattedText
        cost_str = format_cost(self.cost_tracker.total_cost_usd)
        mode = {
            PermissionMode.DEFAULT: "DEFAULT",
            PermissionMode.ACCEPT_EDITS: "ACCEPT EDITS",
            PermissionMode.BYPASS_PERMISSIONS: "BYPASS",
            PermissionMode.PLAN: "PLAN MODE",
        }.get(self.permission_mode, "DEFAULT")
        pct = self._estimate_context_pct()
        filled = int(20 * pct / 100)
        bar = "█" * filled + "░" * (20 - filled)
        parts: list[tuple[str, str]] = [
            ("class:toolbar.model", f" {self._short_model} "),
            ("class:toolbar.sep", "  "),
            ("class:toolbar.mode", mode),
            ("class:toolbar.sep", "  "),
            ("class:toolbar.cost", cost_str),
            ("class:toolbar.sep", "  "),
            ("class:toolbar.bar", f"{bar} {pct:.0f}%"),
            ("class:toolbar.sep", "  "),
        ]
        if self.vim_enabled:
            parts += [("class:toolbar.vim", "VIM"), ("class:toolbar.sep", "  ")]
        if self.plan_mode:
            parts += [("class:toolbar.plan", "PLAN"), ("class:toolbar.sep", "  ")]
        if self.fast_mode:
            parts += [("class:toolbar.fast", "FAST"), ("class:toolbar.sep", "  ")]
        return FormattedText(parts)

    def _build_pt_style(self) -> Any:
        """Build the prompt_toolkit style that matches the dark theme."""
        from prompt_toolkit.styles import Style as PTStyle
        return PTStyle.from_dict({
            "prompt-gt": "bold #D97706",
            "prompt-vim": "bold #A855F7",
            "bottom-toolbar": "bg:#111827 #6B7280",
            "toolbar.model": "bold #D97706",
            "toolbar.mode": "#6B7280",
            "toolbar.cost": "#F9FAFB",
            "toolbar.bar": "#4B5563",
            "toolbar.vim": "bold #A855F7",
            "toolbar.plan": "bold #06B6D4",
            "toolbar.fast": "bold #10B981",
            "toolbar.sep": "#1F2937",
        })

    # ── Streaming helpers ─────────────────────────────────

    @staticmethod
    def _fmt_tool_args(args: dict) -> str:
        """Return a compact one-line summary of the most relevant tool arg."""
        if not args:
            return ""
        for key in ("command", "pattern", "file_path", "path", "url", "query",
                    "question", "prompt", "subject"):
            val = args.get(key)
            if val is not None:
                s = str(val)
                return (s[:70] + "…") if len(s) > 70 else s
        # Fallback — first key
        k, v = next(iter(args.items()))
        s = str(v)
        return (s[:70] + "…") if len(s) > 70 else s

    @staticmethod
    def _fmt_tool_result(tool_name: str, result: Any) -> str:
        """Return a compact one-line result summary for any tool type."""
        if result is None:
            return "done"
        if isinstance(result, dict):
            if result.get("error"):
                return f"error: {result['error']}"
            # Glob
            if "files" in result:
                files = result["files"] or []
                preview = ", ".join(str(f).split("/")[-1] for f in files[:3])
                more = f" +{len(files)-3}" if len(files) > 3 else ""
                return f"{len(files)} file{'s' if len(files) != 1 else ''}: {preview}{more}"
            # Read
            if "numLines" in result:
                return f"{result['numLines']} lines"
            if "content" in result and "filePath" in result:
                lines = str(result["content"]).count("\n") + 1
                return f"{lines} lines"
            # Write
            if "filePath" in result and "isNewFile" in result:
                name = str(result["filePath"]).split("/")[-1]
                action = "created" if result.get("isNewFile") else "updated"
                return f"{action} {name}"
            # Edit
            if "filePath" in result and "content" in result:
                name = str(result["filePath"]).split("/")[-1]
                return f"edited {name}"
            # Grep
            if "matches" in result or "numMatches" in result:
                n = result.get("numMatches") or len(result.get("matches") or [])
                return f"{n} match{'es' if n != 1 else ''}"
            # Bash
            if "stdout" in result or "stderr" in result:
                out = (result.get("stdout") or "").strip()
                err = (result.get("stderr") or "").strip()
                code = result.get("exit_code", 0)
                if code and code != 0:
                    return f"exit {code}" + (f": {err[:60]}" if err else "")
                if out:
                    lines = out.splitlines()
                    return lines[0][:80] + (f"  (+{len(lines)-1} lines)" if len(lines) > 1 else "")
                return "ok"
            return "done"
        if isinstance(result, list):
            if not result:
                return "0 results"
            return f"{len(result)} result{'s' if len(result) != 1 else ''}"
        s = str(result)
        return (s[:80] + "…") if len(s) > 80 else s

    # ── Streaming ─────────────────────────────────────────

    async def _stream_query(self, text: str, query_handler: Callable) -> list[str]:
        """Run query_handler(text) as an async generator, printing tokens live.

        Returns a list of file paths that were written during this turn,
        so the caller can offer to run them.
        """
        self.console.print()
        self.console.print(f"[bold #93C5FD]▌[/] [#93C5FD]{text}[/]")
        self.console.print()

        self.is_streaming = True
        frame: list[int] = [0]
        spin_done: list[bool] = [False]
        first_token: list[bool] = [True]
        written_files: list[str] = []  # collect file paths written this turn

        async def _spin() -> None:
            while not spin_done[0]:
                c = SPINNER_CHARS[frame[0] % len(SPINNER_CHARS)]
                v = SPINNER_VERBS[(frame[0] // 8) % len(SPINNER_VERBS)]
                sys.stdout.write(f"\r\033[2m{c} {v}...\033[0m  ")
                sys.stdout.flush()
                frame[0] += 1
                await asyncio.sleep(0.1)

        spin_task: asyncio.Task = asyncio.create_task(_spin())

        def _clear_spinner() -> None:
            if spin_done[0]:
                return  # already cleared — don't erase printed response content
            spin_done[0] = True
            spin_task.cancel()
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()

        try:
            async for event in query_handler(text):
                if first_token[0]:
                    first_token[0] = False
                    _clear_spinner()
                    # Give cancel a chance to propagate
                    await asyncio.sleep(0)

                if isinstance(event, str):
                    _dlog("tui: str chunk len=%d", len(event))
                    sys.stdout.write(event)
                    sys.stdout.flush()
                elif isinstance(event, dict):
                    etype = event.get("type")
                    _dlog("tui: dict event type=%r keys=%s", etype, list(event.keys()))
                    if etype == "tool_call_start":
                        # Show live "calling tool" indicator as soon as name arrives
                        name = event.get("name", "?")
                        _dlog("tui: tool_call_start name=%r", name)
                        sys.stdout.write(f"\n  ⚙ {name}")
                        sys.stdout.flush()
                    elif etype == "tool_call_args":
                        # Show the key argument for this call (fires before execution)
                        name = event.get("name", "?")
                        args = event.get("args") or {}
                        _dlog("tui: tool_call_args name=%r args=%s", name, str(args)[:200])
                        arg_str = self._fmt_tool_args(args)
                        sys.stdout.write(f"  {arg_str}\n" if arg_str else "\n")
                        sys.stdout.flush()
                    elif etype == "tool_result":
                        tool_name = event.get("tool_name", "?")
                        result = event.get("result", {})
                        args = event.get("args") or {}
                        _dlog("tui: tool_result name=%r result=%s", tool_name, str(result)[:300])
                        if isinstance(result, dict) and result.get("error"):
                            self.console.print(f"  [bold red]✗[/] [dim]{tool_name}:[/dim] [red]{result['error']}[/red]")
                        else:
                            # Track written files so we can offer to run them
                            if tool_name.lower() in ("write", "filewrite", "create_file", "writefile"):
                                fp = (
                                    args.get("file_path")
                                    or args.get("path")
                                    or (result.get("filePath") if isinstance(result, dict) else None)
                                )
                                if fp:
                                    written_files.append(fp)
                            summary = self._fmt_tool_result(tool_name, result)
                            self.console.print(f"  [green]✔[/green] [dim]{summary}[/dim]")
                    else:
                        _dlog("tui: unhandled dict type=%r", etype)
                elif isinstance(event, Message):
                    _dlog("tui: Message role=%r already_streamed=%s content_len=%d",
                          event.role, getattr(event, "already_streamed", False),
                          len(event.content or ""))
                    # Skip assistant messages already streamed token-by-token.
                    # If already_streamed is True, content was printed via chunks.
                    if event.role == "assistant":
                        if not getattr(event, "already_streamed", False) and event.content:
                            sys.stdout.write(event.content)
                            sys.stdout.flush()
                    elif event.role in ("system", "tool") and event.content:
                        sys.stdout.write("\n")
                        self.console.print(f"[dim]{event.content[:300]}[/dim]")
                else:
                    # StreamChunk dataclass or plain dict — both have .choices / ["choices"]
                    choices = (
                        event.choices
                        if hasattr(event, "choices")
                        else event.get("choices", [])
                    )
                    chunk_text = ""
                    for choice in choices:
                        delta = choice.get("delta", {})
                        content = delta.get("content") or ""
                        if content:
                            chunk_text += content
                            sys.stdout.write(content)
                            sys.stdout.flush()
                    if chunk_text:
                        _dlog("tui: StreamChunk len=%d", len(chunk_text))
        except asyncio.CancelledError:
            _dlog("tui: stream CancelledError")
            pass
        except Exception as exc:
            _dlog("tui: stream EXCEPTION %s: %s", type(exc).__name__, exc)
            _clear_spinner()
            self.console.print(f"\n[bold red]Error:[/] {exc}")
        finally:
            _clear_spinner()
            await asyncio.gather(spin_task, return_exceptions=True)
            sys.stdout.write("\n\n")
            sys.stdout.flush()
            self.is_streaming = False

        return written_files

    async def _prompt_run_file(self, file_path: str, session: Any) -> None:
        """Ask the user if they want to run a written file, then exec it."""
        from pathlib import Path as _Path
        import subprocess as _sp

        ext = _Path(file_path).suffix.lower()
        runner_map = {
            ".py": ["python3"],
            ".js": ["node"],
            ".ts": ["npx", "ts-node"],
            ".sh": ["bash"],
            ".rb": ["ruby"],
        }
        runner = runner_map.get(ext)
        if not runner:
            return  # can't run this type

        self.console.print(f"\n[bold #D97706]Run[/] [#F9FAFB]{file_path}[/] [dim]({runner[0]})?[/dim]  [dim]y/n[/dim]")
        try:
            answer: str = await session.prompt_async("> ")
        except (KeyboardInterrupt, EOFError):
            return
        answer = (answer or "").strip().lower()
        if answer not in ("y", "yes"):
            return

        self.console.print(f"\n[dim]Running {file_path}...[/dim]\n")
        try:
            proc = _sp.run(
                runner + [file_path],
                capture_output=False,
                text=True,
            )
            if proc.returncode != 0:
                self.console.print(f"\n[red]Exit code {proc.returncode}[/red]")
        except Exception as exc:
            self.console.print(f"\n[bold red]Error running file:[/] {exc}")
        self.console.print()

    # ── Main loop ──────────────────────────────────────────

    async def run(
        self,
        query_handler: Optional[Callable] = None,
        command_handler: Optional[Callable] = None,
    ) -> None:
        """Run the interactive TUI.

        Args:
            query_handler: async generator ``async def f(text) -> AsyncGenerator``
                           called for each non-command submission; yields tokens /
                           Message objects / OpenAI delta dicts.
            command_handler: async coroutine ``async def f(cmd_line: str)``
                             called for slash commands (without the leading '/').
        """
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
        from ..utils.debug_log import enable_debug
        import pathlib, os
        enable_debug()
        _dlog("tui: run() started model=%s", self.model)

        self._print_welcome()

        _history_path = pathlib.Path(os.path.expanduser("~")) / ".vivian_history"
        session: PromptSession = PromptSession(
            history=FileHistory(str(_history_path)),
            auto_suggest=AutoSuggestFromHistory(),
            style=self._build_pt_style(),
        )

        self._running = True
        buddy_task: Optional[asyncio.Task] = None
        if self.buddy_enabled:
            buddy_task = asyncio.create_task(self._animate_buddy())

        try:
            while self._running:
                try:
                    text: str = await session.prompt_async(
                        self._get_prompt_tokens(),
                        bottom_toolbar=self._get_toolbar,
                    )
                    text = (text or "").strip()
                    if not text:
                        continue

                    if text.startswith("/"):
                        cmd = text[1:]
                        if command_handler is not None:
                            await command_handler(cmd)
                        elif self._on_submit is not None:
                            self._on_submit(text)
                    else:
                        if query_handler is not None:
                            written = await self._stream_query(text, query_handler)
                            # Offer to run any files written during this turn
                            for fp in written:
                                await self._prompt_run_file(fp, session)
                        elif self._on_submit is not None:
                            self._on_submit(text)

                except KeyboardInterrupt:
                    if self.is_streaming:
                        if self._on_interrupt is not None:
                            self._on_interrupt()
                    else:
                        self.console.print(
                            "[dim]  Ctrl+C — press Ctrl+D or type /exit to quit.[/]"
                        )
                except EOFError:
                    self.console.print("\n[dim]Goodbye![/]")
                    break
        finally:
            self._running = False
            if buddy_task is not None:
                buddy_task.cancel()
                await asyncio.gather(buddy_task, return_exceptions=True)

    # ── Background tasks ───────────────────────────────────

    async def _animate_buddy(self) -> None:
        """Keep the buddy sprite ticking."""
        while self._running:
            self.buddy.tick()
            await asyncio.sleep(0.5)

    # ── Helpers ────────────────────────────────────────────

    def _estimate_context_pct(self) -> float:
        total_chars = sum(
            len(m.content or "") + len(str(m.tool_calls or ""))
            for m in self.messages
        )
        max_chars = 100_000 * 4  # ~100 K token context, 4 chars/token
        return min(total_chars / max_chars * 100, 100)

    def compute_panel_layout(self, total_width: Optional[int] = None) -> dict[str, int]:
        """Compute main content and buddy panel widths using yoga flexbox.

        Mirrors the Ink flexbox layout from the original TypeScript TUI:
        - Root: row, width=terminal_width
        - Main content flex=1
        - Buddy panel: fixed 12 cols when enabled, 0 otherwise

        Returns a dict with keys ``main`` and ``buddy`` (pixel/column widths).
        """
        width = total_width or self.console.width or 120
        buddy_cols = 12 if self.buddy_enabled else 0

        if not _HAS_YOGA:
            # Simple fallback without yoga
            return {"main": max(width - buddy_cols, 40), "buddy": buddy_cols}

        root = YogaNode()
        root.setFlexDirection(FlexDirection.Row)
        root.setWidth(float(width))
        root.setHeight(1.0)  # single row for width calculation

        main_child = YogaNode()
        main_child.setFlexGrow(1.0)
        root.insertChild(main_child, 0)

        buddy_child = YogaNode()
        buddy_child.setWidth(float(buddy_cols))
        root.insertChild(buddy_child, 1)

        root.calculateLayout(float(width), 1.0)

        main_w = int(main_child.getComputedWidth())
        buddy_w = int(buddy_child.getComputedWidth())
        return {"main": main_w, "buddy": buddy_w}

