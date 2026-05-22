"""Main CLI entrypoint — mirrors src/main.tsx and src/cli/."""

from __future__ import annotations

import os
import sys

# Support direct script execution (`python cli_main.py`) from inside the
# `vivian_cli` package directory without shadowing stdlib modules like `types`.
if __package__ in (None, ""):
    _script_dir = os.path.abspath(os.path.dirname(__file__))
    # If the script's directory has a local types/ that shadows stdlib, fix sys.path
    if os.path.isdir(os.path.join(_script_dir, "types")):
        _parent_dir = os.path.dirname(_script_dir)
        sys.path = [
            p for p in sys.path
            if os.path.abspath(p or os.getcwd()) != _script_dir
        ]
        if _parent_dir not in sys.path:
            sys.path.insert(0, _parent_dir)
        __package__ = "vivian_cli"

from pathlib import Path

import asyncio
import contextlib
import io
import json
import logging
import re
import shlex
import subprocess
import argparse
import inspect
from typing import Any, Optional

from .api.client import VivianClient
from .query_engine import QueryEngine, ask
from .tools.registry import ToolRegistry
from .tools.all_tools import register_all_tools
from .commands.registry import CommandRegistry
from .commands.all_commands import register_all_commands
from .skills.registry import SkillRegistry, register_all_skills
from .state.store import StateStore
from .cost_tracker import CostTracker
from .services.memory_service import MemoryService
from .services.compact_service import CompactService
from .services.diagnosticTracking import diagnosticTracker
from .services.vivianAiLimits import (
    checkQuotaStatus,
    extractQuotaStatusFromHeaders,
    getRateLimitDisplayName,
)
from .services.rateLimitMessages import (
    getRateLimitMessage,
    getRateLimitErrorMessage,
    isRateLimitErrorMessage,
)
from .services.tokenEstimation import (
    roughTokenCountEstimationForMessages,
    countMessagesTokensWithAPI,
)
from .services.mcp import normalizeNameForMCP, buildMcpToolName, mcpInfoFromString
from .services.analytics import logEvent, attachAnalyticsSink
from .services.tips import getTipToShowOnSpinner, recordShownTip
from .services.oauth import OAuthService
from .services.SessionMemory import (
    getSessionMemoryContent,
    setSessionMemoryConfig,
    isSessionMemoryInitialized,
    resetSessionMemoryState,
)
from .services.extractMemories import initExtractMemories
from .services.remoteManagedSettings import (
    initializeRemoteManagedSettingsLoadingPromise,
    loadRemoteManagedSettings,
    waitForRemoteManagedSettingsToLoad,
)
from .services.settingsSync import uploadUserSettingsInBackground, downloadUserSettings
from .services.teamMemorySync import isTeamMemorySyncAvailable
from .services.PromptSuggestion import shouldEnablePromptSuggestion, abortPromptSuggestion
from .services.plugins import installPlugin, uninstallPlugin, enablePlugin, disablePlugin
from .services.tools import executeToolBatch, StreamingToolExecutor
from .services.toolUseSummary import generateToolUseSummary
from .services.preventSleep import startPreventSleep, stopPreventSleep
from .hooks.registry import HookRegistry
from .plugins.registry import PluginRegistry
from .plugins import (
    initBuiltinPlugins, getBuiltinPlugins, getBuiltinPluginSkillCommands,
)
from .output_styles import getOutputStyleDirStyles, clearOutputStyleCaches
from .bridge.manager import BridgeManager
from .vim.engine import VimEngine
from .utils.history import HistoryManager
from .utils.keybindings import KeybindingManager
from .utils.context import build_system_prompt, get_git_status, get_vivian_md_content
from .utils.config_file import load_config, save_config, write_initial_config
from .types import (
    Message, AppState, PermissionMode, QuerySource,
    ToolDefinition, CommandDefinition, SkillDefinition,
)
from .constants import (
    DEFAULT_BASE_URL, DEFAULT_MODEL, DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE, DEFAULT_TOP_P, DEFAULT_MAX_TURNS,
    PRODUCT_NAME, PRODUCT_VERSION,
)

# Context singletons — mirrors React contexts in TS source
from .context.stats import useStats
from .context.mailbox import useMailbox
from .context.notifications import useNotifications
from .context.voice import useVoice

# Coordinator mode
from .coordinator.coordinatorMode import isCoordinatorMode, getCoordinatorUserContext

# Entrypoints (for programmatic init)
from .entrypoints.init import init as entryInit

# Rich TUI (optional)
try:
    import prompt_toolkit  # noqa: F401
    from .tui.app import VivianTUI
    from .tui.buddy import BuddyManager
    HAS_TUI = True
except ImportError:
    VivianTUI = None  # type: ignore
    BuddyManager = None  # type: ignore
    HAS_TUI = False

logger = logging.getLogger(__name__)


# ── Basic-mode tool display helpers ───────────────────────────────────────────

def _fmt_tool_args_basic(args: dict) -> str:
    """Return a compact one-line summary of the most relevant tool arg."""
    if not args:
        return ""
    for key in ("command", "pattern", "file_path", "path", "url", "query",
                "question", "prompt", "subject"):
        val = args.get(key)
        if val is not None:
            s = str(val)
            return (s[:70] + "…") if len(s) > 70 else s
    k, v = next(iter(args.items()))
    s = str(v)
    return (s[:70] + "…") if len(s) > 70 else s


def _fmt_tool_result_basic(tool_name: str, result) -> str:
    """Return a compact one-line result summary for any tool type."""
    if result is None:
        return "done"
    if isinstance(result, dict):
        if result.get("error"):
            return f"{tool_name}: error: {result['error']}"
        if "files" in result:
            files = result["files"] or []
            preview = ", ".join(str(f).split("/")[-1] for f in files[:3])
            more = f" +{len(files)-3}" if len(files) > 3 else ""
            return f"{len(files)} file{'s' if len(files) != 1 else ''}: {preview}{more}"
        if "numLines" in result:
            return f"{result['numLines']} lines"
        if "content" in result and "filePath" in result:
            lines = str(result["content"]).count("\n") + 1
            return f"{lines} lines"
        if "filePath" in result and "isNewFile" in result:
            name = str(result["filePath"]).split("/")[-1]
            return ("created" if result.get("isNewFile") else "updated") + f" {name}"
        if "filePath" in result and "content" in result:
            return f"edited {str(result['filePath']).split('/')[-1]}"
        if "matches" in result or "numMatches" in result:
            n = result.get("numMatches") or len(result.get("matches") or [])
            return f"{n} match{'es' if n != 1 else ''}"
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
        return f"{tool_name}: done"
    if isinstance(result, list):
        return f"{len(result)} result{'s' if len(result) != 1 else ''}"
    s = str(result)
    return (s[:80] + "…") if len(s) > 80 else s


class VivianCLI:
    """Main Vivian CLI application — the Python equivalent of the full TypeScript system."""

    # ── Shell command detection ────────────────────────────────────────
    _SHELL_COMMAND_RE = re.compile(
        r'^(?:'
        r'ls|cd|mv|cp|rm|mkdir|rmdir|touch|cat|head|tail|less|more|'
        r'grep|find|locate|which|whereis|echo|printf|export|unset|'
        r'pwd|whoami|id|date|env|printenv|chmod|chown|chgrp|'
        r'ln|df|du|mount|umount|ps|kill|top|htop|free|uptime|'
        r'ping|curl|wget|ssh|scp|rsync|tar|gzip|gunzip|zip|unzip|'
        r'diff|patch|sort|uniq|wc|tr|cut|sed|awk|xargs|tee|'
        r'source|\.|alias|unalias|type|command|builtin|exec|'
        r'git|docker|kubectl|npm|yarn|pip|python|python3|node|'
        r'npx|cargo|rustc|go|java|javac|make|cmake|gcc|g\+\+|'
        r'systemctl|service|journalctl|'
        r'sudo|su|'
        r'clear|reset|history|fc|'
        r'man|info|whatis|apropos|'
        r'basename|dirname|realpath|readlink|stat|file|'
        r'awk|perl|ruby|php|'
        r'vim|nano|emacs|code|nvim|'
        r'tmux|screen|'
        r'fg|bg|jobs|disown|nohup|'
        r'time|nice|renice|'
        r'ip|ifconfig|netstat|ss|route|'
        r'crontab|at|batch|'
        r'useradd|usermod|userdel|groupadd|passwd|'
        r'snap|apt|apt-get|dnf|yum|pacman|brew|flatpak|'
        r'w|who|last|lastlog|'
        r'hostname|uname|arch|'
        r'shred|dd|'
        r'strace|ltrace|gdb|lsof|'
        r'rsync|nc|ncat|telnet|'
        r'watch|'
        r'open|xdg-open|'
        r'cal|bc|expr|'
        r'seq|yes|sleep|true|false|test|\[\[?'
        r')'
        r'(?:\s|$)'
    )

    # Words that indicate the user is chatting, not running a command
    _CHAT_INDICATOR_RE = re.compile(
        r'\b(?:'
        r'can you|could you|would you|will you|please|what|how|why|when|where|who|'
        r'tell me|show me|explain|describe|find|search|look|check|read|write|'
        r'help me|i need|i want|i\'m|i am|is there|are there|do you|does|'
        r'run this|execute this|do this|can i|could i|should i|'
        r'what\'s|what is|how do|how to|how can|how should|'
        r'\?|^hi\b|^hey\b|^hello\b|^okay\b|^ok\b|^thanks\b|^thank you\b'
        r')\b'
    )

    _SHELL_BUILTINS = frozenset({'cd', 'export', 'unset', 'alias', 'unalias',
                                  'source', '.', 'pwd', 'echo', 'clear', 'history'})

    def _is_shell_command(self, text: str) -> bool:
        """Check if input is a standalone shell command (not chat).

        Returns True ONLY if:
        - The text starts with a known shell command
        - It does NOT contain chat indicators (questions, "can you", "please", etc.)
        - It is NOT a slash command

        A sentence like "can you ls the directory?" goes to the AI.
        A bare command like "ls -la" runs directly.
        """
        stripped = text.strip()
        if not stripped:
            return False
        if stripped.startswith('/'):
            return False

        # Must start with a known shell command
        if not self._SHELL_COMMAND_RE.match(stripped):
            return False

        # If it contains chat indicators, it's a sentence — send to AI
        if self._CHAT_INDICATOR_RE.search(stripped):
            return False

        return True

    def _run_shell_command(self, cmd: str) -> dict:
        """Execute a shell command and return the result.

        Returns {"stdout": str, "stderr": str, "exit_code": int, "cwd": str}.
        """
        parts = shlex.split(cmd)
        if not parts:
            return {"stdout": "", "stderr": "", "exit_code": 0, "cwd": self.cwd}

        cmd_name = parts[0]

        # Handle built-in commands in-process
        if cmd_name == 'cd':
            target = parts[1] if len(parts) > 1 else os.path.expanduser('~')
            try:
                new_cwd = str(Path(target).resolve())
                os.chdir(new_cwd)
                self.cwd = new_cwd
                return {"stdout": f"Changed directory to {self.cwd}", "stderr": "", "exit_code": 0, "cwd": self.cwd}
            except Exception as e:
                return {"stdout": "", "stderr": str(e), "exit_code": 1, "cwd": self.cwd}

        if cmd_name == 'pwd':
            return {"stdout": self.cwd, "stderr": "", "exit_code": 0, "cwd": self.cwd}

        if cmd_name == 'export':
            if len(parts) >= 2:
                for arg in parts[1:]:
                    if '=' in arg:
                        k, v = arg.split('=', 1)
                        os.environ[k] = v
                return {"stdout": "", "stderr": "", "exit_code": 0, "cwd": self.cwd}
            return {"stdout": "\n".join(f"{k}={v}" for k, v in os.environ.items()),
                    "stderr": "", "exit_code": 0, "cwd": self.cwd}

        if cmd_name == 'clear':
            os.system('clear' if os.name != 'nt' else 'cls')
            return {"stdout": "", "stderr": "", "exit_code": 0, "cwd": self.cwd}

        if cmd_name == 'history':
            entries = self.history_manager.get_recent(50)
            return {"stdout": "\n".join(f"  {i}: {e}" for i, e in enumerate(entries)),
                    "stderr": "", "exit_code": 0, "cwd": self.cwd}

        if cmd_name == 'echo':
            return {"stdout": " ".join(parts[1:]) if len(parts) > 1 else "",
                    "stderr": "", "exit_code": 0, "cwd": self.cwd}

        # External command — run via subprocess
        try:
            result = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.cwd,
                env=os.environ.copy(),
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "cwd": self.cwd,
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "Command timed out after 30s", "exit_code": 124, "cwd": self.cwd}
        except FileNotFoundError:
            return {"stdout": "", "stderr": f"Command not found: {cmd_name}", "exit_code": 127, "cwd": self.cwd}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "exit_code": 1, "cwd": self.cwd}

    # ── End shell command system ───────────────────────────────────────

    def __init__(
        self,
        api_key: Optional[str] = None,
        admin_jwt: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        permission_mode: PermissionMode = PermissionMode.DEFAULT,
        cwd: str = "",
        username: Optional[str] = None,
        max_turns: int = DEFAULT_MAX_TURNS,
        max_budget_usd: Optional[float] = None,
        custom_system_prompt: Optional[str] = None,
        append_system_prompt: Optional[str] = None,
        verbose: bool = False,
        debug: bool = False,
    ):
        # Config
        self.base_url = base_url
        self.model = model
        self.permission_mode = permission_mode
        self.cwd = str(Path(cwd).resolve()) if cwd else os.getcwd()
        self.username = username
        self.max_turns = max_turns
        self.max_budget_usd = max_budget_usd
        self.custom_system_prompt = custom_system_prompt
        self.append_system_prompt = append_system_prompt
        self.verbose = verbose
        self.debug = debug
        self.config = load_config()

        # Setup logging
        level = logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)
        logging.basicConfig(
            level=level,
            format="%(asctime)s  %(levelname)-7s  %(message)s",
            datefmt="%H:%M:%S",
        )

        # ── Resolve provider settings ─────────────────────────────────────
        # If a provider other than "vivian" is configured, override base_url,
        # api_key and model from the provider registry — unless the caller
        # explicitly passed non-default values (CLI flags take precedence).
        from .api.providers.registry import resolve_client_config
        _provider = self.config.get("provider", "vivian")
        _resolved = resolve_client_config(self.config, _provider)

        # Caller-supplied api_key / base_url always win
        _eff_api_key  = api_key  if api_key  else _resolved["api_key"]
        _eff_base_url = base_url if base_url != DEFAULT_BASE_URL else _resolved["base_url"]
        _eff_model    = model    if model    != DEFAULT_MODEL     else (
            self.config.get("model") or _resolved["default_model"] or model
        )
        _auth_style    = _resolved["auth_style"]
        _extra_headers = _resolved["extra_headers"]

        # Store the effective model / base_url on self
        self.model    = _eff_model
        self.base_url = _eff_base_url

        # Core client
        self.client = VivianClient(
            api_key=_eff_api_key,
            admin_jwt=admin_jwt,
            base_url=_eff_base_url,
            default_model=_eff_model,
            auth_style=_auth_style,
            extra_headers=_extra_headers,
        )

        # Registries
        self.tool_registry = ToolRegistry()
        self.command_registry = CommandRegistry()
        self.skill_registry = SkillRegistry()
        self.hook_registry = HookRegistry()
        self.plugin_registry = PluginRegistry()

        # Register all built-ins
        register_all_tools(self.tool_registry)
        register_all_commands(self.command_registry)
        register_all_skills(self.skill_registry)

        # Register custom skills from ~/.vivian/skills/ and .vivian/skills/
        from .skills.load_skills_dir import load_skills_dir
        for skills_dir in (Path.home() / ".vivian" / "skills", Path(self.cwd) / ".vivian" / "skills"):
            for custom_skill in load_skills_dir(skills_dir):
                self.skill_registry.register(SkillDefinition(
                    name=custom_skill.name,
                    description=custom_skill.description,
                    prompt=custom_skill.get_prompt_for_command("", None),
                    source="custom",
                    is_enabled=True,
                ))

        # Initialise bundled plugins and register their skill-commands
        initBuiltinPlugins()
        for cmd in getBuiltinPluginSkillCommands():
            try:
                self.command_registry.register(CommandDefinition(
                    name=cmd["name"],
                    description=cmd.get("description", ""),
                    type=CommandDefinition.__fields__["type"].default  # type: ignore[attr-defined]
                    if hasattr(CommandDefinition, "__fields__") else None,
                    source=cmd.get("source", "builtin"),
                ))
            except Exception:
                pass  # registry.register may throw on duplicate; skip gracefully

        # Output styles (async; loaded lazily in start())
        self._output_styles: list[dict] = []

        # State & services
        self.state_store = StateStore()
        self.cost_tracker = CostTracker()
        self.memory_service = MemoryService(self.client)
        self.compact_service = CompactService()
        self.bridge_manager = BridgeManager()
        self.vim_engine = VimEngine()
        self.history_manager = HistoryManager()
        self.keybinding_manager = KeybindingManager()
        from .keybindings import KeybindingSetup
        self.keybinding_context = KeybindingSetup()

        # New services wired in
        self.oauth_service = OAuthService()
        self.streaming_tool_executor: Optional[StreamingToolExecutor] = None
        self._extract_memories = initExtractMemories()

        # Context singletons (mirrors React context providers in TS)
        self.stats = useStats()
        self.mailbox = useMailbox()
        self.notifications = useNotifications()
        self.voice = useVoice()

        # Coordinator mode state
        self._coordinator_mode = isCoordinatorMode()

        # Boot remote managed settings and settings sync in background
        initializeRemoteManagedSettingsLoadingPromise()
        try:
            downloadUserSettings()
        except Exception:
            pass

        # Query engine (created per-session)
        self._engine: Optional[QueryEngine] = None

        # Running state
        self._running = False
        self._vim_enabled = False

    @property
    def query_engine(self) -> QueryEngine:
        return self.engine

    def set_setting(self, key: str, value: Any) -> None:
        self.config[key] = value
        save_config(self.config)

    async def _invoke_local_command(self, handler: Any, args: str = "") -> str:
        from .types.command import CompactResult, SkipResult, TextResult

        signature = inspect.signature(handler)
        positional = [
            param
            for param in signature.parameters.values()
            if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]

        if len(positional) >= 2:
            result = handler(args, self)
        elif len(positional) == 1:
            first_name = positional[0].name.lower()
            if "context" in first_name:
                result = handler(self)
            else:
                result = handler(args)
        else:
            result = handler()

        if inspect.isawaitable(result):
            result = await result

        if isinstance(result, TextResult):
            return result.value
        if isinstance(result, CompactResult):
            return result.displayText or ""
        if isinstance(result, SkipResult):
            return ""
        return str(result)

    @property
    def engine(self) -> QueryEngine:
        if self._engine is None:
            self._engine = QueryEngine(
                self.client,
                tool_registry=self.tool_registry,
                commands=self.command_registry.get_enabled_commands(),
                model=self.model,
                max_turns=self.max_turns,
                max_budget_usd=self.max_budget_usd,
                permission_mode=self.permission_mode,
                username=self.username,
                cwd=self.cwd,
                custom_system_prompt=self.custom_system_prompt,
                append_system_prompt=self.append_system_prompt,
                coordinator_mode=self._coordinator_mode,
            )
        return self._engine

    async def start(self):
        """Start the CLI with the Rich TUI matching the original vivian Code look."""
        self._running = True

        # Run entrypoints init (config, bootstrap state, OAuth, preconnect)
        try:
            await entryInit()
        except Exception:
            pass

        # Initialize diagnostics tracker
        try:
            diagnosticTracker.initialize()
        except Exception:
            pass

        # Load output styles for the current working directory
        try:
            self._output_styles = await getOutputStyleDirStyles(self.cwd)
        except Exception:
            self._output_styles = []

        # Load remote managed settings (non-fatal on failure)
        try:
            await loadRemoteManagedSettings()
        except Exception:
            pass

        # Wait for remote managed settings before proceeding
        try:
            await waitForRemoteManagedSettingsToLoad()
        except Exception:
            pass

        # Notify if coordinator mode is active
        if self._coordinator_mode:
            print("[Coordinator mode active — workers will be spawned via Agent tool]")

        if HAS_TUI and VivianTUI is not None:
            await self._start_tui()
        else:
            await self._start_basic()

    async def _start_tui(self):
        """Start with the Rich + prompt_toolkit TUI."""
        self._tui = VivianTUI(
            model=self.model,
            base_url=self.base_url,
            permission_mode=self.permission_mode,
            cost_tracker=self.cost_tracker,
            vim_enabled=self._vim_enabled,
            buddy_enabled=True,
        )
        self._tui.session_id = self.engine.get_session_id()

        # Show git status
        git_status = await get_git_status(self.cwd)
        if git_status:
            self._tui.add_message(Message(role="system", content=git_status))

        # Show vivian.md
        vivian_md = get_vivian_md_content(self.cwd)
        if vivian_md:
            self._tui.add_message(Message(role="system", content=f"[Loaded vivian.md ({len(vivian_md)} chars)]"))

        # Keep legacy interrupt callback wired
        self._tui.set_on_interrupt(self._handle_tui_interrupt)

        # Run with proper handlers — query_handler is an async generator,
        # command_handler is the existing async _handle_command coroutine.
        await self._tui.run(
            query_handler=self._tui_query_stream,
            command_handler=self._handle_command,
        )

    async def _tui_query_stream(self, prompt: str):
        """Async generator that streams query events to the TUI."""
        self.history_manager.add(prompt)
        try:
            async for event in self.engine.submit_message(
                prompt, query_source=QuerySource.REPL_MAIN
            ):
                yield event
        except Exception as exc:
            yield Message(role="system", content=f"Error: {exc}")
        finally:
            pass

    def _handle_tui_submit(self, text: str):
        """Handle a prompt submission from the TUI."""
        if text.startswith("/"):
            asyncio.create_task(self._handle_command(text[1:]))
            return
        if not text.strip():
            return
        self.history_manager.add(text)
        self._tui.add_message(Message(role="user", content=text))
        asyncio.create_task(self._process_tui_query(text))

    def _handle_tui_interrupt(self):
        """Handle interrupt from the TUI."""
        self.engine.interrupt()
        self._tui.set_streaming(False)

    async def _process_tui_query(self, prompt: str):
        """Process a query and stream results to the TUI."""
        self._tui.set_streaming(True)
        self._tui.set_spinner(0)

        try:
            _tui_chunks_streamed = False
            async for event in self.engine.submit_message(
                prompt, query_source=QuerySource.REPL_MAIN
            ):
                if isinstance(event, Message):
                    # Skip re-printing text already shown token-by-token
                    if getattr(event, "already_streamed", False):
                        continue
                    if event.role == "assistant" and event.content:
                        self._tui.append_stream(event.content)
                    elif event.role == "system":
                        self._tui.add_message(event)
                elif hasattr(event, "choices"):
                    for choice in event.choices:
                        delta = choice.get("delta", {})
                        if delta.get("content"):
                            _tui_chunks_streamed = True
                            self._tui.append_stream(delta["content"])
                elif isinstance(event, dict):
                    event_type = event.get("type")
                    if event_type == "tool_call_start":
                        name = event.get("name", "?")
                        self._tui.add_tool_start(name)
                    elif event_type == "tool_result":
                        result = event.get("result", {})
                        tool_name = event.get("tool_name", "")
                        if isinstance(result, dict) and "error" in result:
                            self._tui.add_tool_error(tool_name, result["error"])
                        else:
                            self._tui.add_tool_success(tool_name, result)
        except Exception as e:
            self._tui.add_message(Message(role="system", content=f"Error: {e}"))
        finally:
            self._tui.set_streaming(False)

    async def _start_basic(self):
        """Fallback basic terminal mode."""
        print(f"╭────────────────────────────────────────╮")
        print(f"│  {PRODUCT_NAME} v{PRODUCT_VERSION}                     │")
        print(f"│  Provider: {self.config.get('provider','vivian'):<28} │")
        print(f"│  Model: {self.model:<30} │")
        print(f"│  API:   {self.base_url:<30} │")
        print(f"╰────────────────────────────────────────╯")
        print()
        print("Type a message to chat, or /help for commands.")
        print("Install full TUI deps: pip install rich prompt_toolkit")
        print()

        git_status = await get_git_status(self.cwd)
        if git_status:
            print(git_status)
            print()

        vivian_md = get_vivian_md_content(self.cwd)
        if vivian_md:
            print(f"[Loaded vivian.md ({len(vivian_md)} chars)]")
            print()

        await self._repl_loop()

    async def _repl_loop(self):
        """Main REPL (Read-Eval-Print Loop)."""
        while self._running:
            try:
                # Read
                prompt = await self._read_input()
                if prompt is None:
                    continue

                # Handle slash commands
                if prompt.startswith("/"):
                    await self._handle_command(prompt[1:])
                    continue

                # Handle empty input
                if not prompt.strip():
                    continue

                # ── Shell command interception ──────────────────────────
                if self._is_shell_command(prompt):
                    await self._handle_shell_command(prompt)
                    continue
                # ── End shell interception ──────────────────────────────

                # Add to history
                self.history_manager.add(prompt)

                # Eval — submit to query engine
                print()
                async for event in self.engine.submit_message(
                    prompt, query_source=QuerySource.REPL_MAIN
                ):
                    await self._render_event(event)

                print()

            except KeyboardInterrupt:
                print("\n[Interrupted]")
                self.engine.interrupt()
            except EOFError:
                print("\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"REPL error: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
                print(f"Error: {e}")

    async def _handle_shell_command(self, cmd: str):
        """Execute a shell command, display output, and inject into conversation."""
        self.history_manager.add(cmd)

        # Run the command
        result = self._run_shell_command(cmd)

        # Display output
        if result["stdout"]:
            print(result["stdout"])
        if result["stderr"]:
            print(result["stderr"], file=sys.stderr)

        # Inject into conversation so the AI remembers it
        shell_msg = (
            f"[shell] $ {cmd}\n"
            + (f"stdout:\n{result['stdout']}\n" if result["stdout"] else "")
            + (f"stderr:\n{result['stderr']}\n" if result["stderr"] else "")
            + f"exit: {result['exit_code']}"
        )
        self.engine.messages.append(Message(role="user", content=shell_msg))
        self.engine.messages.append(Message(
            role="system",
            content=f"Shell command completed (exit {result['exit_code']}). "
                    f"Working directory: {result['cwd']}"
        ))

    async def _read_input(self) -> Optional[str]:
        """Read user input with VIM support if enabled."""
        try:
            if self._vim_enabled:
                return await self._read_vim_input()
            else:
                return input("$> ")
        except (KeyboardInterrupt, EOFError):
            raise

    async def _read_vim_input(self) -> Optional[str]:
        """Read input in VIM mode."""
        # Simplified VIM input — full implementation would use raw terminal I/O
        print("[VIM] ", end="", flush=True)
        return input()

    async def _render_event(self, event: Any):
        """Render a streaming event to the terminal."""
        if isinstance(event, Message):
            # Skip assistant messages that were already printed token-by-token
            # as streaming chunks — printing them again would duplicate the text.
            if getattr(event, "already_streamed", False):
                return
            if event.role == "assistant" and event.content:
                print(event.content, end="", flush=True)
            elif event.role == "system":
                print(f"\n  ℹ {event.content}")
        elif hasattr(event, "choices"):
            # StreamChunk — print each token as it arrives
            for choice in event.choices:
                delta = choice.get("delta", {})
                if delta.get("content"):
                    print(delta["content"], end="", flush=True)
        elif isinstance(event, dict):
            event_type = event.get("type")
            if event_type == "tool_call_start":
                # Show the tool name the moment the model starts calling it
                name = event.get("name", "?")
                print(f"\n  ⚙ {name}", end="", flush=True)
            elif event_type == "tool_call_args":
                # Show the key argument (fires just before tool execution)
                args = event.get("args") or {}
                arg_str = _fmt_tool_args_basic(args)
                print(f"  {arg_str}" if arg_str else "", flush=True)
            elif event_type == "tool_result":
                tool_name = event.get("tool_name", "")
                result = event.get("result", "")
                args = event.get("args") or {}
                if isinstance(result, dict) and "error" in result:
                    print(f"  ✗ {tool_name}: {result['error']}")
                else:
                    summary = _fmt_tool_result_basic(tool_name, result)
                    print(f"  ✔ {summary}")

    async def _handle_command(self, cmd_line: str):
        """Handle a slash command."""
        parts = cmd_line.strip().split(maxsplit=1)
        cmd_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        tui = getattr(self, "_tui", None)

        # Built-in commands
        if cmd_name in ("exit", "quit", "q"):
            from .commands.exit.exit import call as exitCommand

            self._running = False
            if tui:
                tui.stop()
            print(await self._invoke_local_command(exitCommand, args))
        elif cmd_name in ("help", "h"):
            from .commands.help.help import call as helpCommand
            print(await self._invoke_local_command(helpCommand, args))
        elif cmd_name == "clear":
            from .commands.clear.clear import call as clearCommand
            print(await self._invoke_local_command(clearCommand, args))
        elif cmd_name == "model":
            from .commands.model.model import call as modelCommand
            print(await self._invoke_local_command(modelCommand, args))
        elif cmd_name == "cost":
            from .commands.cost.cost import call as costCommand
            print(await self._invoke_local_command(costCommand, args))
        elif cmd_name == "usage":
            from .commands.usage.usage import call as usageCommand
            print(await self._invoke_local_command(usageCommand, args))
        elif cmd_name == "vim":
            from .commands.vim.vim import call as vimCommand
            print(await self._invoke_local_command(vimCommand, args))
        elif cmd_name == "plan":
            from .commands.plan.plan import call as planCommand
            print(await self._invoke_local_command(planCommand, args))
        elif cmd_name == "fast":
            from .commands.fast.fast import call as fastCommand
            print(await self._invoke_local_command(fastCommand, args))
        elif cmd_name == "session":
            from .commands.session.session import call as sessionCommand
            print(await self._invoke_local_command(sessionCommand, args))
        elif cmd_name == "status":
            from .commands.status.status import call as statusCommand
            print(await self._invoke_local_command(statusCommand, args))
        elif cmd_name == "memory":
            from .commands.memory.memory import call as memoryCommand
            print(await self._invoke_local_command(memoryCommand, args))
        elif cmd_name == "skills":
            from .commands.skills.skills import call as skillsCommand
            print(await self._invoke_local_command(skillsCommand, args))
        elif cmd_name == "tools":
            from .commands.tools.tools import call as toolsCommand
            print(await self._invoke_local_command(toolsCommand, args))
        elif cmd_name == "keybindings":
            from .commands.keybindings.keybindings import call as keybindingsCommand
            print(await self._invoke_local_command(keybindingsCommand, args))
        elif cmd_name == "history":
            from .commands.history.history import call as historyCommand
            print(await self._invoke_local_command(historyCommand, args))
        elif cmd_name == "version":
            from .commands.version import call as versionCommand
            print(await self._invoke_local_command(versionCommand, args))
        elif cmd_name == "provider":
            from .commands.provider.provider import call as providerCommand
            print(await self._invoke_local_command(providerCommand, args))
        elif cmd_name in ("setup", "setup-wizard"):
            from .utils.setup_wizard import run_setup_wizard
            from .utils.config_file import save_config as _save_cfg
            from .api.providers.registry import resolve_client_config
            new_cfg = run_setup_wizard()
            _save_cfg(new_cfg)
            self.config.update(new_cfg)
            # Reconfigure the live client with the new provider
            _pid = new_cfg.get("provider", "vivian")
            _resolved = resolve_client_config(self.config, _pid)
            from .api.client import VivianClient as _VC
            import asyncio as _asyncio
            try:
                _loop = _asyncio.get_event_loop()
                if not _loop.is_closed():
                    await self.client.close()
            except Exception:
                pass
            self.client = _VC(
                api_key=_resolved["api_key"],
                base_url=_resolved["base_url"],
                default_model=_resolved["default_model"] or self.model,
                auth_style=_resolved["auth_style"],
                extra_headers=_resolved["extra_headers"],
            )
            self._engine = None
            print(f"Configuration updated. Provider: {_pid}")
        elif cmd_name == "config":
            from .commands.config.config import call as configCommand
            print(await self._invoke_local_command(configCommand, args))
        elif cmd_name == "compact":
            from .commands.compact.compact import call as compactCommand
            print(await self._invoke_local_command(compactCommand, args))
        elif cmd_name == "export":
            from .commands.export.export import call as exportCommand
            print(await self._invoke_local_command(exportCommand, args))
        elif cmd_name == "copy":
            from .commands.copy.copy import call as copyCommand
            print(await self._invoke_local_command(copyCommand, args))
        elif cmd_name == "stats":
            from .commands.stats.stats import call as statsCommand
            print(await self._invoke_local_command(statsCommand, args))
        elif cmd_name == "doctor":
            from .commands.doctor.doctor import call as doctorCommand
            print(await self._invoke_local_command(doctorCommand, args))
        elif cmd_name == "limits":
            from .commands.limits import call as limitsCommand
            print(await self._invoke_local_command(limitsCommand, args))
        elif cmd_name == "tip":
            from .commands.tip import call as tipCommand
            print(await self._invoke_local_command(tipCommand, args))
        elif cmd_name == "session-memory":
            from .commands.session_memory import call as sessionMemoryCommand
            print(await self._invoke_local_command(sessionMemoryCommand, args))
        elif cmd_name == "token-count":
            from .commands.token_count import call as tokenCountCommand
            print(await self._invoke_local_command(tokenCountCommand, args))
        elif cmd_name == "mcp":
            from .commands.mcp.mcp import call as mcpCommand
            print(await self._invoke_local_command(mcpCommand, args))
        elif cmd_name == "team-memory":
            from .commands.team_memory import call as teamMemoryCommand
            print(await self._invoke_local_command(teamMemoryCommand, args))
        elif cmd_name == "plugin":
            from .commands.plugin.plugin import call as pluginCommand
            print(await self._invoke_local_command(pluginCommand, args))
        elif cmd_name == "buddy":
            if tui and tui.buddy:
                tui.buddy.pet()
                print("Pet the buddy! ♥")
            else:
                print("Buddy not available (install 'rich' for full TUI)")
        # ── Additional commands from TS source ──
        elif cmd_name == "theme":
            from .commands.theme.theme import call as themeCommand
            print(await self._invoke_local_command(themeCommand, args))
        elif cmd_name == "color":
            from .commands.color.color import call as colorCommand
            print(await self._invoke_local_command(colorCommand, args))
        elif cmd_name == "feedback":
            from .commands.feedback.feedback import call as feedbackCommand
            print(await self._invoke_local_command(feedbackCommand, args))
        elif cmd_name == "release-notes":
            from .commands.release_notes.release_notes import call as releaseNotesCommand
            print(await self._invoke_local_command(releaseNotesCommand, args))
        elif cmd_name == "rename":
            from .commands.rename.rename import call as renameCommand
            print(await self._invoke_local_command(renameCommand, args))
        elif cmd_name == "resume":
            from .commands.resume.resume import resumeSession
            if args:
                result = await resumeSession(args, self)
                print(getattr(result, 'value', result))
            else:
                result = await resumeSession("", self)
                print(getattr(result, 'value', result))
        elif cmd_name == "rewind":
            from .commands.rewind.rewind import rewindConversation
            steps = int(args) if args.isdigit() else 1
            print(await self._invoke_local_command(rewindConversation, str(steps)))
        elif cmd_name == "upgrade":
            from .commands.upgrade.upgrade import call as upgradeCommand
            print(await self._invoke_local_command(upgradeCommand, args))
        elif cmd_name == "update":
            await self._cmd_update(args)
        elif cmd_name == "login":
            from .commands.login.login import login_cmd
            print(await self._invoke_local_command(login_cmd, args))
        elif cmd_name == "logout":
            from .commands.logout.logout import logout_cmd
            print(await self._invoke_local_command(logout_cmd, args))
        elif cmd_name == "voice":
            from .commands.voice.voice import call as voiceCommand
            print(await self._invoke_local_command(voiceCommand, args))
        elif cmd_name == "ide":
            from .commands.ide.ide import ideInfo
            print(await self._invoke_local_command(ideInfo, args))
        elif cmd_name == "desktop":
            from .commands.desktop.desktop import desktopInfo
            print(await self._invoke_local_command(desktopInfo, args))
        elif cmd_name == "mobile":
            from .commands.mobile.mobile import mobileInfo
            print(await self._invoke_local_command(mobileInfo, args))
        elif cmd_name == "bridge":
            from .commands.bridge.bridge import call as bridgeCommand
            print(await self._invoke_local_command(bridgeCommand, args))
        elif cmd_name == "permissions":
            from .commands.permissions.permissions import call as permissionsCommand
            print(await self._invoke_local_command(permissionsCommand, args))
        elif cmd_name == "privacy-settings":
            from .commands.privacy_settings.privacy_settings import call as privacySettingsCommand
            print(await self._invoke_local_command(privacySettingsCommand, args))
        elif cmd_name == "sandbox-toggle":
            from .commands.sandbox_toggle.sandbox_toggle import call as sandboxToggleCommand
            print(await self._invoke_local_command(sandboxToggleCommand, args))
        elif cmd_name == "terminal-setup":
            from .commands.terminalSetup.terminalSetup import setupTerminal
            print(await self._invoke_local_command(setupTerminal, args))
        elif cmd_name == "remote-setup":
            from .commands.remote_setup.remote_setup import setupRemote
            print(await self._invoke_local_command(setupRemote, args))
        elif cmd_name == "remote-env":
            from .commands.remote_env.remote_env import showRemoteEnv
            print(await self._invoke_local_command(showRemoteEnv, args))
        elif cmd_name == "reload-plugins":
            from .commands.reload_plugins.reload_plugins import call as reloadPluginsCommand
            print(await self._invoke_local_command(reloadPluginsCommand, args))
        elif cmd_name == "rate-limit-options":
            from .commands.rate_limit_options.rate_limit_options import showRateLimitOptions
            print(await self._invoke_local_command(showRateLimitOptions, args))
        elif cmd_name == "extra-usage":
            from .commands.extra_usage.extra_usage import call as extraUsageCommand
            print(await self._invoke_local_command(extraUsageCommand, args))
        elif cmd_name == "output-style":
            from .commands.output_style.output_style import call as outputStyleCommand
            print(await self._invoke_local_command(outputStyleCommand, args))
        elif cmd_name == "stickers":
            from .commands.stickers.stickers import showStickers
            print(await self._invoke_local_command(showStickers, args))
        elif cmd_name == "tag":
            from .commands.tag.tag import call as tagCommand
            print(await self._invoke_local_command(tagCommand, args))
        elif cmd_name == "tasks":
            from .commands.tasks.tasks import showTasks
            print(await self._invoke_local_command(showTasks, args))
        elif cmd_name == "thinkback":
            from .commands.thinkback.thinkback import showThinkback
            print(await self._invoke_local_command(showThinkback, args))
        elif cmd_name == "thinkback-play":
            from .commands.thinkback_play.thinkback_play import playThinkback
            print(await self._invoke_local_command(playThinkback, args))
        elif cmd_name == "btw":
            from .commands.btw.btw import btwMessage
            print(await self._invoke_local_command(btwMessage, args))
        elif cmd_name == "app":
            from .commands.app import call as appCommand
            print(await self._invoke_local_command(appCommand, args))
        elif cmd_name == "advisor":
            from .commands.advisor import advisorInfo
            print(await self._invoke_local_command(advisorInfo, args))
        elif cmd_name == "bridge-kick":
            from .commands.bridge_kick import kickBridge
            print(await self._invoke_local_command(kickBridge, args))
        elif cmd_name == "brief":
            from .commands.brief import call as briefCommand
            print(await self._invoke_local_command(briefCommand, args))
        elif cmd_name == "commit":
            from .commands.commit import commitMessage
            print(await self._invoke_local_command(commitMessage, args))
        elif cmd_name == "commit-push-pr":
            from .commands.commit_push_pr import commitPushPR
            print(await self._invoke_local_command(commitPushPR, args))
        elif cmd_name == "init":
            from .commands.init import initProject
            print(await self._invoke_local_command(initProject, args))
        elif cmd_name == "init-verifiers":
            from .commands.init_verifiers import initVerifiers
            print(await self._invoke_local_command(initVerifiers, args))
        elif cmd_name == "insights":
            from .commands.insights import showInsights
            print(await self._invoke_local_command(showInsights, args))
        elif cmd_name == "install":
            from .commands.install import installVivian
            print(await self._invoke_local_command(installVivian, args))
        elif cmd_name == "review":
            from .commands.review import reviewCode
            print(await self._invoke_local_command(reviewCode, args))
        elif cmd_name == "security-review":
            from .commands.security_review import securityReview
            print(await self._invoke_local_command(securityReview, args))
        elif cmd_name == "ultraplan":
            from .commands.ultraplan import call as ultraplanCommand
            print(await self._invoke_local_command(ultraplanCommand, args))
        elif cmd_name == "context":
            from .commands.context.context_noninteractive import call as contextCommand
            print(await self._invoke_local_command(contextCommand, args))
        elif cmd_name == "diff":
            from .commands.diff.diff import showDiff
            print(await self._invoke_local_command(showDiff, args))
        elif cmd_name == "effort":
            from .commands.effort.effort import call as effortCommand
            print(await self._invoke_local_command(effortCommand, args))
        elif cmd_name == "files":
            from .commands.files.files import showFiles
            print(await self._invoke_local_command(showFiles, args))
        elif cmd_name == "hooks":
            from .commands.hooks.hooks import call as hooksCommand
            print(await self._invoke_local_command(hooksCommand, args))
        elif cmd_name == "mcp-status":
            from .commands.mcp.mcp import showMcpStatus
            print(await self._invoke_local_command(showMcpStatus, args))
        elif cmd_name == "passes":
            from .commands.passes.passes import showPasses
            print(await self._invoke_local_command(showPasses, args))
        elif cmd_name == "plugin-info":
            from .commands.plugin.plugin import pluginInfo
            print(await self._invoke_local_command(pluginInfo, args))
        elif cmd_name == "pr-comments":
            from .commands.pr_comments.pr_comments import showPRComments
            print(await self._invoke_local_command(showPRComments, args))
        elif cmd_name == "branch":
            from .commands.branch.branch import branchInfo
            print(await self._invoke_local_command(branchInfo, args))
        elif cmd_name == "chrome":
            from .commands.chrome.chrome import chromeInfo
            print(await self._invoke_local_command(chromeInfo, args))
        elif cmd_name == "agents":
            from .commands.agents.agents import showAgents
            print(await self._invoke_local_command(showAgents, args))
        elif cmd_name == "add-dir":
            from .commands.add_dir.add_dir import call as addDirCommand
            print(await self._invoke_local_command(addDirCommand, args))
        elif cmd_name == "install-github-app":
            from .commands.install_github_app.install_github_app import installGitHubApp
            print(await self._invoke_local_command(installGitHubApp, args))
        elif cmd_name == "install-slack-app":
            from .commands.install_slack_app.install_slack_app import installSlackApp
            print(await self._invoke_local_command(installSlackApp, args))
        elif cmd_name == "heapdump":
            from .commands.heapdump.heapdump import call as heapdumpCommand
            print(await self._invoke_local_command(heapdumpCommand, args))
        elif cmd_name in ("desktop-gui", "desktopgui"):
            import threading
            from .web_gui import launch_web_gui
            from .desktop_webgui import launch_desktop_gui
            _ide_url = "http://127.0.0.1:7878/"
            threading.Thread(
                target=launch_web_gui,
                kwargs=dict(
                    runtime_or_engine=self,
                    host="127.0.0.1",
                    port=7878,
                    open_browser=False,
                ),
                daemon=True,
                name="vivian-ide",
            ).start()
            threading.Thread(
                target=launch_desktop_gui,
                kwargs=dict(
                    runtime=self,
                    host="127.0.0.1",
                    port=7979,
                    open_browser=True,
                    workspace=self.cwd,
                    ide_url=_ide_url,
                ),
                daemon=True,
                name="vivian-desktop",
            ).start()
            print("[Desktop GUI] Desktop → http://127.0.0.1:7979/  |  IDE → http://127.0.0.1:7878/")
        else:
            print(f"Unknown command: /{cmd_name} (type /help for available commands)")

    async def execute_slash_command(self, cmd_line: str) -> str:
        """Execute a slash command and return captured stdout/stderr text."""
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            await self._handle_command(cmd_line)
        output = (buf_out.getvalue() + buf_err.getvalue()).strip()
        return output or "(no output)"

    def get_runtime_capabilities(self) -> dict[str, Any]:
        """Return a JSON-safe snapshot of CLI capabilities for GUI/WebGUI parity."""
        command_defs = self.command_registry.get_enabled_commands()
        tool_defs = self.tool_registry.get_enabled_tools()
        skill_defs = self.skill_registry.get_enabled_skills()
        return {
            "model": self.model,
            "cwd": self.cwd,
            "commands": [
                {
                    "name": c.name,
                    "description": c.description,
                    "source": c.source,
                    "aliases": list(c.aliases or []),
                    "type": c.type.value if hasattr(c.type, "value") else str(c.type),
                }
                for c in command_defs
            ],
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "source": t.source.value if hasattr(t.source, "value") else str(t.source),
                    "aliases": list(t.aliases or []),
                    "requires_permission": bool(getattr(t, "requires_permission", False)),
                }
                for t in tool_defs
            ],
            "skills": [
                {
                    "name": s.name,
                    "description": s.description,
                    "source": s.source,
                    "triggers": list(s.triggers or []),
                }
                for s in skill_defs
            ],
            "counts": {
                "commands": len(command_defs),
                "tools": len(tool_defs),
                "skills": len(skill_defs),
                "plugins": len(self.plugin_registry),
                "hooks": sum(len(h) for h in self.hook_registry._hooks.values()),
            },
            "systems": {
                "task_system": True,
                "plugin_system": True,
                "skill_system": True,
                "services": True,
                "servers": True,
                "proxy": True,
                "utilities": True,
            },
        }

    def _show_help(self, tui=None):
        """Show help text."""
        help_text = """
Available Commands:
  /help, /h          Show this help
  /exit, /quit, /q   Exit Vivian CLI
  /clear             Clear the screen
  /model [name]      View or change the model
  /provider          List/switch AI provider (Vivian, Ollama, OpenAI, Groq…)
  /setup             Re-run the setup wizard to switch provider/credentials
  /cost              Show session cost
  /usage             Show usage statistics
  /vim               Toggle VIM mode
  /plan              Enter plan mode
  /fast              Toggle fast mode
  /session           Show session info
  /status            Show system status
  /memory            Show Vivian's memory
  /skills            List available skills
  /tools             List available tools
  /keybindings       Show keybindings
  /history           Show command history
  /version           Show version
  /config            Show configuration
  /compact           Compact conversation
  /export            Export conversation
  /copy              Copy last response
  /stats             Show system stats
  /doctor            Run diagnostics
  /update [branch]   Pull latest code from GitHub (git pull origin <branch>)
  /limits            Show rate limit / quota status
  /tip               Show a tip
  /session-memory    Show session memory
  /token-count       Estimate token count for current conversation
  /mcp info <name>   Parse MCP tool string
  /team-memory       Show team memory sync status
  /plugin <action>   install|uninstall|enable|disable a plugin
  /buddy             Pet the buddy companion

────────────────────────────────────────────────────────
  Security & Pentesting Tools
  (tell Vivian: "use ssh connect <host>" / "scan <url>")
────────────────────────────────────────────────────────

SSHTool — Persistent SSH sessions:
  connect <host>              Connect (password or key auth)
  exec <command>              Run command on connected host
  disconnect / status         Close session / show info
  upload <local> <remote>     Upload file via SCP
  download <remote> <local>   Download file via SCP
  port_forward <lp> <rh> <rp> SSH port forwarding
  scan_ports <host> [range]   Port scan from remote host
  check_sudo / find_suid      Sudo check / SUID binaries
  enum_system                 Full system recon

TryHackMeTool — CTF / pentest workflow:
  vpn_connect <config>        Connect to TryHackMe VPN
  vpn_status / vpn_disconnect VPN management
  nmap_scan <ip>              Service/version discovery
  gobuster <url> <wordlist>   Directory enumeration
  nikto_scan <url>            Web vulnerability scan
  hydra_brute <svc> <t> <u> <wl>  Credential brute force
  enum4linux <ip>             SMB/Windows enumeration
  smb_client <ip> [share]     SMB share access
  sqlmap <url>                SQL injection testing
  john_crack <hash_file>      Hash cracking
  linpeas_upload <ip>         Upload & run linpeas
  submit_flag <flag>          Record captured flag
  flags_found                 List flags this session
  room_info <name>            Fetch room details
  check_tools                 Check installed CTF tools

AutoPentestTool — Autonomous pentest framework:
  auto_pwn <target>           Autonomous scan→exploit→flags
  quick_scan / deep_scan      Fast / full port+CVE scan
  cve_scan <target>           Map services to CVEs
  web_attack / php_exploit / java_exploit / smb_exploit
  ftp_exploit / ssh_brute     Targeted exploitation
  vuln_lookup <svc> <ver>     100+ CVE cross-reference
  exploit_search <cve|kw>     ExploitDB / Metasploit search
  kotb_defend / kotb_attack   KOTH defense / attack
  web_enum / privesc_check    Web enum / privesc vectors

VulnScannerTool — SAST (200+ patterns, 9 languages):
  scan <path> [lang]          Auto-detect language scan
  scan_php/java/python/js/c/go/ruby/dotnet  Lang scans
  scan_sql / scan_xss / scan_injection      Vuln-type scans
  scan_secrets / scan_crypto / scan_config  Secrets/crypto/config
  audit_deps <path>           pip-audit + npm audit
  report                      Consolidated last-scan report

WebAuditTool — Live OWASP Top 10 web scanner:
  full_scan <url>             Complete OWASP audit
  sqli_test / xss_test / csrf_check / ssrf_test
  path_traversal / auth_check / headers_check / cors_check
  ssl_check / info_disclosure / dir_enum / form_fuzz
  cookie_audit / api_scan     Per-topic targeted checks

CodeAuditTool — Deep audit + taint tracking:
  audit <path>                Full audit
  taint_track <path> <src> <sink>  Data flow tracking
  auth_audit / crypto_audit / input_audit / session_audit
  file_audit / db_audit / api_audit / dependency_check
  compliance_check <path> owasp_asvs  ASVS mapping
  fix_report                  Prioritized remediation plan
  diff_audit <old> <new>      Audit changed code

THMWriteupTool — Write-up DB + auto-exploit engine:
  search <room_name>          Search GitHub + web for write-ups
  ingest_github <name>        Auto-ingest top write-ups from GitHub
  fingerprint <ip>            Identify which THM room a target is
  auto_exploit <ip>           Auto-exploit using write-up knowledge
  kotb_speedrun <ip>          KOTH speed-run with pre-loaded exploits
  db_list / db_search / db_show  Browse the write-up database
  db_stats / db_export / db_import  Manage the database
  build_index                 Rebuild room fingerprint index

ParsecVisionTool — Screen capture overlay + AI object detection:
  start [window_title]        Start OpenGL overlay on a window
  stop / status               Stop overlay / check status
  capture [path]              Capture annotated screenshot
  db_add <name> <path>        Add image to recognition database
  db_remove / db_list         Manage image database
  db_match <path>             Match image against database
  db_match_screen             Match current screen against DB
  detect_objects [thresh]     Detect moving objects on screen
  label_objects               Label detected objects with AI
  motion_regions              Show motion detection regions
  configure <key> <val>       Change sensitivity/FPS/colors
  check_deps                  Check OpenCV/OpenGL dependencies
────────────────────────────────────────────────────────

Keybindings:
  Ctrl+C             Interrupt current operation
  Ctrl+D             Exit
  Ctrl+R             Search history
  Ctrl+L             Clear screen
  Up/Down            Navigate history
  Tab                Autocomplete
  Escape             Cancel

Type any message to chat with Vivian.
"""
        if tui:
            tui.add_message(Message(role="system", content=help_text))
        else:
            print(help_text)

    async def _show_memory(self):
        """Show Vivian's memory."""
        try:
            core = await self.memory_service.get_core_memories()
            if core:
                print("Core Memory:")
                for m in core[:10]:
                    print(f"  [{m.get('category', '')}] {m.get('key', '')}: {m.get('value', '')}")
            episodic = await self.memory_service.get_episodic_memories(limit=5)
            if episodic:
                print("Recent Episodic Memory:")
                for m in episodic:
                    print(f"  {m.get('summary', m.get('content', ''))[:100]}")
        except Exception as e:
            print(f"Memory unavailable: {e}")

    async def _cmd_update(self, args: str = "") -> None:
        """
        /update [branch]

        Pull the latest code for the entire project from the GitHub remote.
        Walks up from this file until it finds a .git directory, then runs
        `git pull` (optionally `git pull origin <branch>`).
        Shows the git output line-by-line and prompts to restart when done.
        """
        import subprocess as _sp
        from pathlib import Path as _P

        tui = getattr(self, "_tui", None)

        def _emit(text: str) -> None:
            if tui:
                from .types import Message as _Msg
                tui.add_message(_Msg(role="system", content=text))
            else:
                print(text)

        # ── locate git root ─────────────────────────────────────────────
        start = _P(__file__).resolve().parent
        git_root: "Optional[_P]" = None
        for candidate in [start] + list(start.parents):
            if (candidate / ".git").exists():
                git_root = candidate
                break

        if git_root is None:
            _emit("❌  /update: no .git directory found — is this a git repository?")
            return

        # ── show current state ─────────────────────────────────────────
        try:
            _branch = _sp.run(
                ["git", "-C", str(git_root), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=10).stdout.strip()
            _remote = _sp.run(
                ["git", "-C", str(git_root), "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:
            _branch, _remote = "unknown", "unknown"

        _emit(f"🔄  Updating project from GitHub…")
        _emit(f"    Repo root : {git_root}")
        _emit(f"    Remote    : {_remote or '(none)'}")
        _emit(f"    Branch    : {_branch}")

        # ── build pull command ─────────────────────────────────────────
        target_branch = args.strip() or _branch
        pull_cmd = ["git", "-C", str(git_root), "pull", "--rebase=false",
                    "origin", target_branch]

        _emit(f"    Running   : {' '.join(pull_cmd[2:])}\n")

        # ── run git pull (streaming output) ────────────────────────────
        try:
            proc = _sp.Popen(
                pull_cmd,
                stdout=_sp.PIPE, stderr=_sp.STDOUT,
                text=True, bufsize=1)
            lines: list[str] = []
            if proc.stdout:
                for line in proc.stdout:
                    stripped = line.rstrip()
                    lines.append(stripped)
                    _emit(f"  {stripped}")
            proc.wait(timeout=120)
            rc = proc.returncode
        except FileNotFoundError:
            _emit("❌  git not found in PATH. Install Git and ensure it is on PATH.")
            return
        except _sp.TimeoutExpired:
            _emit("❌  git pull timed out after 120 s.")
            return
        except Exception as exc:
            _emit(f"❌  git pull failed: {exc}")
            return

        # ── report result ───────────────────────────────────────────────
        if rc == 0:
            already_up_to_date = any(
                "already up to date" in l.lower() or
                "already up-to-date" in l.lower()
                for l in lines)
            if already_up_to_date:
                _emit("\n✅  Already up to date — no changes pulled.")
            else:
                _emit("\n✅  Update complete. Restart the CLI to load the new code:")
                _emit("       python -m vivian_cli  (or  python cli_main.py)")
        else:
            _emit(f"\n❌  git pull exited with code {rc}.")
            _emit("    Check the output above for merge conflicts or auth issues.")

    async def shutdown(self):
        """Clean shutdown."""
        self._running = False
        await self.client.close()
        # Save cost state
        print(f"\n{self.cost_tracker.format_total_cost()}")


async def main():
    """Main entrypoint for the Vivian CLI."""
    # ── First-launch setup wizard ─────────────────────────────────────────
    # Run before arg parsing so the saved config is available immediately.
    # Skip wizard when: non-interactive stdin, --version, or --prompt flags,
    # or when config already exists with setup_complete=True.
    from .utils.config_file import is_first_launch, save_config as _save_cfg
    _wizard_skip_flags = {"--version", "-v", "--prompt", "-p", "--json",
                          "--admin-login", "--gui", "--web-gui", "--desktop-gui",
                          "--no-wizard"}
    _interactive = sys.stdin.isatty()
    _skip_wizard  = (
        not _interactive
        or any(f in sys.argv for f in _wizard_skip_flags)
        or not is_first_launch()
    )
    if not _skip_wizard:
        from .utils.setup_wizard import run_setup_wizard
        wizard_cfg = run_setup_wizard()
        _save_cfg(wizard_cfg)

    # Load config from ~/.vivian/config.json (env vars override)
    config = load_config()

    parser = argparse.ArgumentParser(
        description=f"{PRODUCT_NAME} — Python client for Vivian AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Config: ~/.vivian/config.json
  api_url:  {config['api_url']}
  username: {config['username'] or '(not set)'}
  model:    {config['model']}

Examples:
  vivian                              Start interactive REPL
  vivian -p "Write a hello world"     One-shot query
  vivian --model qwen3.6:27b          Use specific model
  vivian --api-key viv-xxx            Override API key
  vivian --admin-login                Login as admin
        """,
    )

    # API options (defaults from config file)
    parser.add_argument("--api-key", default=config["api_key"] or None,
                        help="Vivian API key")
    parser.add_argument("--admin-jwt", help="Admin JWT token")
    parser.add_argument("--base-url", default=config["api_url"],
                        help="API base URL")
    parser.add_argument("--username", default=config["username"] or None,
                        help="Username for per-user memory")

    # Model options
    parser.add_argument("--model", "-m", default=config["model"],
                        help="Model to use")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--top-p", type=float, default=DEFAULT_TOP_P)

    # Session options
    parser.add_argument("--max-turns", type=int, default=config.get("max_turns", DEFAULT_MAX_TURNS))
    parser.add_argument("--max-budget", type=float, default=config.get("max_budget_usd"),
                        help="Max budget in USD")
    parser.add_argument("--permission-mode", default=config.get("permission_mode", "default"),
                        choices=["default", "acceptEdits", "bypassPermissions", "plan"])
    parser.add_argument("--cwd", "-C", default=os.getcwd(), help="Working directory (default: current directory)")

    # Prompt options
    parser.add_argument("--prompt", "-p", help="One-shot prompt (non-interactive)")
    parser.add_argument("--system-prompt", help="Custom system prompt")
    parser.add_argument("--append-system-prompt", help="Append to system prompt")
    parser.add_argument("--system-prompt-file", help="Load system prompt from file")

    # Output options
    parser.add_argument("--verbose", "-v", action="store_true",
                        default=config.get("verbose", False), help="Verbose output")
    parser.add_argument("--debug", action="store_true",
                        default=config.get("debug", False), help="Debug output")
    parser.add_argument("--json", action="store_true", help="JSON output mode")
    parser.add_argument("--stream", action="store_true", default=True, help="Stream output")

    # Admin options
    parser.add_argument("--admin-login", action="store_true", help="Login as admin")
    parser.add_argument("--admin-username", default="admin")
    parser.add_argument("--admin-password", help="Admin password")

    # Misc
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--vim", action="store_true",
                        default=config.get("vim_enabled", False), help="Start in VIM mode")
    parser.add_argument("--no-buddy", action="store_true", help="Disable buddy companion")
    parser.add_argument("--gui", action="store_true",
                        help="Launch the Qt GUI IDE (folder tree, tabbed editor, AI chat) instead of the terminal REPL")
    parser.add_argument("--gui-path", default="",
                        help="With --gui: file or folder to open at startup (defaults to --cwd)")
    parser.add_argument("--web-gui", action="store_true",
                        help="Launch the browser-based IDE (HTML+Monaco) on localhost — same features as --gui, plus Web Serial for ESP32 monitor")
    parser.add_argument("--web-port", type=int, default=7878,
                        help="With --web-gui: TCP port to bind (default 7878)")
    parser.add_argument("--web-host", default="127.0.0.1",
                        help="With --web-gui: interface to bind (default 127.0.0.1 — use 0.0.0.0 to expose to LAN)")
    parser.add_argument("--no-open-browser", action="store_true",
                        help="With --web-gui: don't auto-open the browser")
    parser.add_argument("--desktop-gui", action="store_true",
                        help="Launch the cyberpunk Desktop GUI (port 7979) + web IDE (port 7878) in the browser")
    parser.add_argument("--desktop-port", type=int, default=7979,
                        help="With --desktop-gui: TCP port for the desktop shell (default 7979)")
    parser.add_argument("--desktop-host", default="127.0.0.1",
                        help="With --desktop-gui: interface to bind (default 127.0.0.1)")
    parser.add_argument("--no-wizard", action="store_true",
                        help="Skip the first-launch setup wizard even if no config exists")

    args = parser.parse_args()

    # Resolve cwd to absolute path immediately so all tools see the real launch dir
    args.cwd = str(Path(args.cwd).resolve())
    os.chdir(args.cwd)  # also set process cwd to match

    # Version
    if args.version:
        print(f"{PRODUCT_NAME} v{PRODUCT_VERSION}")
        return

    # Load system prompt from file
    custom_system_prompt = args.system_prompt
    if args.system_prompt_file:
        try:
            custom_system_prompt = Path(args.system_prompt_file).read_text()
        except Exception as e:
            print(f"Error reading system prompt file: {e}")
            sys.exit(1)

    # Admin login
    api_key = args.api_key or os.environ.get("VIVIAN_API_KEY")
    admin_jwt = args.admin_jwt

    # Normalize base URL: strip trailing /v1 since the client adds it
    base_url = args.base_url.rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]

    if args.admin_login:
        password = args.admin_password or os.environ.get("VIVIAN_ADMIN_PASSWORD")
        if not password:
            import getpass
            password = getpass.getpass("Admin password: ")

        temp_client = VivianClient(base_url=base_url)
        try:
            admin_jwt = await temp_client.admin.login(args.admin_username, password)
            print(f"Admin login successful.")
        except Exception as e:
            print(f"Admin login failed: {e}")
            sys.exit(1)
        finally:
            await temp_client.close()

    # Create CLI
    cli = VivianCLI(
        api_key=api_key,
        admin_jwt=admin_jwt,
        base_url=base_url,
        model=args.model,
        permission_mode=PermissionMode(args.permission_mode),
        cwd=args.cwd,
        username=args.username,
        max_turns=args.max_turns,
        max_budget_usd=args.max_budget,
        custom_system_prompt=custom_system_prompt,
        append_system_prompt=args.append_system_prompt,
        verbose=args.verbose,
        debug=args.debug,
    )

    if args.vim:
        cli._vim_enabled = True
    if args.no_buddy:
        cli._buddy_enabled = False

    try:
        if args.desktop_gui:
            # Desktop GUI — start web_gui IDE in a background thread, then
            # launch the cyberpunk desktop shell as the blocking server.
            import threading
            from .web_gui import launch_web_gui
            from .desktop_webgui import launch_desktop_gui
            ide_host = args.web_host
            ide_port = args.web_port
            ide_url  = f"http://{ide_host}:{ide_port}/"
            ide_thread = threading.Thread(
                target=launch_web_gui,
                kwargs=dict(
                    runtime_or_engine=cli,
                    host=ide_host,
                    port=ide_port,
                    open_browser=False,
                ),
                daemon=True,
                name="vivian-ide",
            )
            ide_thread.start()
            launch_desktop_gui(
                runtime=cli,
                host=args.desktop_host,
                port=args.desktop_port,
                open_browser=not args.no_open_browser,
                workspace=args.cwd,
                ide_url=ide_url,
            )
            sys.exit(0)
        elif args.web_gui:
            # Browser IDE — stdlib HTTP server, SSE streaming, Monaco editor.
            from .web_gui import launch_web_gui
            rc = launch_web_gui(cli,
                                host=args.web_host, port=args.web_port,
                                open_browser=not args.no_open_browser)
            sys.exit(rc)
        elif args.gui:
            # Qt GUI mode — runs Qt's event loop on the main thread; the engine
            # is driven from a worker asyncio loop inside the AI panel.
            from .gui import launch_gui
            initial_path = args.gui_path or args.cwd
            rc = launch_gui(cli, initial_path=initial_path)
            sys.exit(rc)
        elif args.prompt:
            # One-shot mode
            async for event in cli.engine.submit_message(
                args.prompt, query_source=QuerySource.HEADLESS
            ):
                if args.json:
                    if isinstance(event, Message):
                        print(json.dumps({"role": event.role, "content": event.content}))
                    elif isinstance(event, dict):
                        print(json.dumps(event))
                else:
                    await cli._render_event(event)
            print()
        else:
            # Interactive REPL
            await cli.start()
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        await cli.shutdown()


def run():
    """Synchronous entrypoint."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
