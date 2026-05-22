"""All built-in command definitions for Vivian CLI.

Mirrors src/commands/* — every slash command from the TypeScript codebase.
"""

from __future__ import annotations

from typing import Any, Optional

from .registry import CommandRegistry
from ..types import CommandDefinition, CommandType


# ── All Commands ───────────────────────────────────────────

COMMANDS: list[CommandDefinition] = [
    # Session & Navigation
    CommandDefinition(
        name="clear", description="Clear the conversation screen",
        type=CommandType.LOCAL, aliases=["cls"],
    ),
    CommandDefinition(
        name="compact", description="Compact the conversation context to save tokens",
        type=CommandType.PROMPT, progress_message="compacting conversation",
    ),
    CommandDefinition(
        name="exit", description="Exit Vivian CLI",
        type=CommandType.LOCAL, aliases=["quit", "q"],
    ),
    CommandDefinition(
        name="help", description="Show help and available commands",
        type=CommandType.LOCAL, aliases=["h"],
    ),
    CommandDefinition(
        name="resume", description="Resume a previous conversation",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="session", description="Show current session info",
        type=CommandType.LOCAL,
    ),

    # Configuration
    CommandDefinition(
        name="config", description="View or modify configuration",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="model", description="Switch the active model",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="theme", description="Change the terminal theme",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="color", description="Change color settings",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="output-style", description="Change output verbosity style",
        type=CommandType.LOCAL, aliases=["outputStyle"],
    ),
    CommandDefinition(
        name="permissions", description="Configure tool permissions",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="privacy-settings", description="Configure privacy settings",
        type=CommandType.LOCAL, aliases=["privacySettings"],
    ),
    CommandDefinition(
        name="hooks", description="Manage hooks configuration",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="keybindings", description="View and customize keybindings",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="vim", description="Toggle VIM mode",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="voice", description="Toggle voice mode",
        type=CommandType.LOCAL,
    ),

    # Git & Version Control
    CommandDefinition(
        name="init", description="Initialize a vivian.md file for the project",
        type=CommandType.PROMPT, progress_message="initializing project",
    ),
    CommandDefinition(
        name="commit", description="Generate a git commit message",
        type=CommandType.PROMPT, progress_message="generating commit message",
    ),
    CommandDefinition(
        name="commit-push-pr", description="Commit, push, and create a PR",
        type=CommandType.PROMPT, progress_message="creating PR",
        aliases=["commitPushPr", "cpr"],
    ),
    CommandDefinition(
        name="review", description="Review code changes",
        type=CommandType.PROMPT, progress_message="reviewing changes",
    ),
    CommandDefinition(
        name="security-review", description="Security-focused code review",
        type=CommandType.PROMPT, progress_message="reviewing security",
        aliases=["securityReview"],
    ),
    CommandDefinition(
        name="pr_comments", description="Review PR comments",
        type=CommandType.PROMPT, progress_message="reviewing PR comments",
        aliases=["prComments"],
    ),
    CommandDefinition(
        name="diff", description="Show and explain git diff",
        type=CommandType.PROMPT, progress_message="analyzing diff",
    ),
    CommandDefinition(
        name="branch", description="Create or switch git branches",
        type=CommandType.LOCAL,
    ),

    # Code Analysis
    CommandDefinition(
        name="doctor", description="Diagnose and fix project issues",
        type=CommandType.PROMPT, progress_message="running diagnostics",
    ),
    CommandDefinition(
        name="app", description="Launch a GUI app (memedit, ueSDKgen)",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="advisor", description="Get architectural advice",
        type=CommandType.PROMPT, progress_message="analyzing architecture",
    ),
    CommandDefinition(
        name="insights", description="Generate session analytics report",
        type=CommandType.PROMPT, progress_message="analyzing sessions",
    ),
    CommandDefinition(
        name="brief", description="Generate a session brief",
        type=CommandType.PROMPT, progress_message="generating brief",
    ),
    CommandDefinition(
        name="effort", description="Estimate effort for a task",
        type=CommandType.PROMPT, progress_message="estimating effort",
    ),

    # Cost & Usage
    CommandDefinition(
        name="cost", description="Show session cost summary",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="usage", description="Show detailed usage statistics",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="extra-usage", description="Show extra usage details",
        type=CommandType.LOCAL, aliases=["extraUsage"],
    ),

    # Files & Context
    CommandDefinition(
        name="add-dir", description="Add a directory to the workspace context",
        type=CommandType.LOCAL, aliases=["addDir"],
    ),
    CommandDefinition(
        name="context", description="Show current context information",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="files", description="List files in the conversation context",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="copy", description="Copy the last response to clipboard",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="export", description="Export the conversation",
        type=CommandType.LOCAL,
    ),

    # Tools & Plugins
    CommandDefinition(
        name="mcp", description="Manage MCP server connections",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="plugin", description="Manage plugins",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="reload-plugins", description="Reload all plugins",
        type=CommandType.LOCAL, aliases=["reloadPlugins"],
    ),
    CommandDefinition(
        name="skills", description="List available skills",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="agents", description="Manage custom agents",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="tasks", description="Manage background tasks",
        type=CommandType.LOCAL,
    ),

    # Memory
    CommandDefinition(
        name="memory", description="View or edit Vivian's memory",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="session-memory", description="Show extracted session memory",
        type=CommandType.LOCAL, aliases=["sessionMemory"],
    ),
    CommandDefinition(
        name="team-memory", description="Show team memory sync status",
        type=CommandType.LOCAL, aliases=["teamMemory"],
    ),

    # IDE Integration
    CommandDefinition(
        name="ide", description="Configure IDE integration",
        type=CommandType.LOCAL,
    ),

    # Misc
    CommandDefinition(
        name="status", description="Show system status",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="statusline", description="Toggle status line display",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="stats", description="Show detailed statistics",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="limits", description="Show vivian AI rate limits",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="tip", description="Show a contextual tip",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="token-count", description="Estimate conversation token count",
        type=CommandType.LOCAL, aliases=["tokenCount"],
    ),
    CommandDefinition(
        name="feedback", description="Send feedback",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="release-notes", description="Show release notes",
        type=CommandType.LOCAL, aliases=["releaseNotes"],
    ),
    CommandDefinition(
        name="upgrade", description="Check for and apply upgrades",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="version", description="Show version information",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="plan", description="Enter plan mode for the next request",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="fast", description="Toggle fast mode",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="rename", description="Rename the current conversation",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="tag", description="Tag the current conversation",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="rewind", description="Rewind the conversation to an earlier point",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="thinkback", description="Review past thinking",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="thinkback-play", description="Replay past thinking",
        type=CommandType.LOCAL, aliases=["thinkbackPlay"],
    ),
    CommandDefinition(
        name="btw", description="Send a 'by the way' message",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="desktop", description="Desktop integration commands",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="mobile", description="Mobile integration commands",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="chrome", description="Chrome extension integration",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="terminalSetup", description="Configure terminal settings",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="sandbox-toggle", description="Toggle sandbox mode",
        type=CommandType.LOCAL, aliases=["sandboxToggle"],
    ),
    CommandDefinition(
        name="passes", description="Show available passes/features",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="login", description="Log in to Vivian",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="logout", description="Log out of Vivian",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="install-github-app", description="Install the GitHub App",
        type=CommandType.LOCAL, aliases=["installGitHubApp"],
    ),
    CommandDefinition(
        name="install-slack-app", description="Install the Slack App",
        type=CommandType.LOCAL, aliases=["installSlackApp"],
    ),
    CommandDefinition(
        name="remote-env", description="Configure remote environment",
        type=CommandType.LOCAL, aliases=["remoteEnv"],
    ),
    CommandDefinition(
        name="rate-limit-options", description="Configure rate limit options",
        type=CommandType.LOCAL, aliases=["rateLimitOptions"],
    ),
    CommandDefinition(
        name="stickers", description="Manage stickers",
        type=CommandType.LOCAL,
    ),
    CommandDefinition(
        name="heapdump", description="Generate a heap dump for debugging",
        type=CommandType.LOCAL,
    ),
]


def register_all_commands(registry: CommandRegistry):
    """Register all built-in commands with their handlers."""
    # Register command definitions
    for cmd in COMMANDS:
        registry.register(cmd)

    # ── Wire handlers ──────────────────────────────────────
    _wire_handler(registry, "clear", "clear.clear", "call")
    _wire_handler(registry, "exit", "exit.exit", "call")
    _wire_handler(registry, "help", "help.help", "call")
    _wire_handler(registry, "resume", "resume.resume", "call")
    _wire_handler(registry, "session", "session.session", "call")
    _wire_handler(registry, "rename", "rename.rename", "call")
    _wire_handler(registry, "rewind", "rewind.rewind", "call")
    _wire_handler(registry, "compact", "compact.compact", "call")

    _wire_handler(registry, "config", "config.config", "call")
    _wire_handler(registry, "model", "model.model", "call")
    _wire_handler(registry, "theme", "theme.theme", "call")
    _wire_handler(registry, "color", "color.color", "call")
    _wire_handler(registry, "permissions", "permissions.permissions", "call")
    _wire_handler(registry, "hooks", "hooks.hooks", "call")
    _wire_handler(registry, "keybindings", "keybindings.keybindings", "call")
    _wire_handler(registry, "vim", "vim.vim", "call")
    _wire_handler(registry, "voice", "voice.voice", "call")
    _wire_handler(registry, "sandbox-toggle", "sandbox_toggle.sandbox_toggle", "call")
    _wire_handler(registry, "privacy-settings", "privacy_settings.privacy_settings", "call")
    _wire_handler(registry, "output-style", "output_style.output_style", "call")

    _wire_handler(registry, "commit", "commit", "call")
    _wire_handler(registry, "commit-push-pr", "commit_push_pr", "call")
    _wire_handler(registry, "review", "review", "call")
    _wire_handler(registry, "diff", "diff.diff", "call")
    _wire_handler(registry, "branch", "branch.branch", "call")
    _wire_handler(registry, "init", "init", "call")
    _wire_handler(registry, "pr_comments", "pr_comments.pr_comments", "call")

    _wire_handler(registry, "doctor", "doctor.doctor", "call")
    _wire_handler(registry, "app", "app", "call")
    _wire_handler(registry, "advisor", "advisor", "call")
    _wire_handler(registry, "effort", "effort.effort", "call")
    _wire_handler(registry, "brief", "brief", "call")
    _wire_handler(registry, "init-verifiers", "init_verifiers", "call")
    _wire_handler(registry, "security-review", "security_review", "call")

    _wire_handler(registry, "cost", "cost.cost", "call")
    _wire_handler(registry, "usage", "usage.usage", "call")
    _wire_handler(registry, "extra-usage", "extra_usage.extra_usage", "call")
    _wire_handler(registry, "add-dir", "add_dir.add_dir", "call")
    _wire_handler(registry, "context", "context.context", "call")
    _wire_handler(registry, "files", "files.files", "call")
    _wire_handler(registry, "copy", "copy.copy", "call")
    _wire_handler(registry, "export", "export.export", "call")

    _wire_handler(registry, "mcp", "mcp.mcp", "call")
    _wire_handler(registry, "plugin", "plugin.plugin", "call")
    _wire_handler(registry, "skills", "skills.skills", "call")
    _wire_handler(registry, "reload-plugins", "reload_plugins.reload_plugins", "call")
    _wire_handler(registry, "memory", "memory.memory", "call")
    _wire_handler(registry, "session-memory", "session_memory", "call")
    _wire_handler(registry, "team-memory", "team_memory", "call")
    _wire_handler(registry, "agents", "agents.agents", "call")
    _wire_handler(registry, "tasks", "tasks.tasks", "call")
    _wire_handler(registry, "tools", "tools.tools", "call")

    _wire_handler(registry, "status", "status.status", "call")
    _wire_handler(registry, "stats", "stats.stats", "call")
    _wire_handler(registry, "limits", "limits", "call")
    _wire_handler(registry, "tip", "tip", "call")
    _wire_handler(registry, "token-count", "token_count", "call")
    _wire_handler(registry, "plan", "plan.plan", "call")
    _wire_handler(registry, "fast", "fast.fast", "call")
    _wire_handler(registry, "feedback", "feedback.feedback", "call")
    _wire_handler(registry, "ide", "ide.ide", "call")
    _wire_handler(registry, "desktop", "desktop.desktop", "call")
    _wire_handler(registry, "terminalSetup", "terminalSetup.terminalSetup", "call")
    _wire_handler(registry, "tag", "tag.tag", "call")
    _wire_handler(registry, "stickers", "stickers.stickers", "call")
    _wire_handler(registry, "version", "version", "call")
    _wire_handler(registry, "upgrade", "upgrade.upgrade", "call")
    _wire_handler(registry, "history", "history.history", "call")

    # ── Bridge & Remote ────────────────────────────────────
    _wire_handler(registry, "bridge", "bridge.bridge", "call")
    _wire_handler(registry, "bridge-kick", "bridge_kick", "call")
    _wire_handler(registry, "remote-env", "remote_env.remote_env", "call")
    _wire_handler(registry, "remote-setup", "remote_setup.remote_setup", "call")

    # ── Integration ────────────────────────────────────────
    _wire_handler(registry, "chrome", "chrome.chrome", "call")
    _wire_handler(registry, "mobile", "mobile.mobile", "call")
    _wire_handler(registry, "login", "login.login", "call")
    _wire_handler(registry, "logout", "logout.logout", "call")
    _wire_handler(registry, "install", "install", "call")

    # ── Analysis & Insights ────────────────────────────────
    _wire_handler(registry, "insights", "insights", "call")
    _wire_handler(registry, "thinkback", "thinkback.thinkback", "call")
    _wire_handler(registry, "thinkback-play", "thinkback_play.thinkback_play", "call")
    _wire_handler(registry, "ultraplan", "ultraplan", "call")
    _wire_handler(registry, "btw", "btw.btw", "call")
    _wire_handler(registry, "passes", "passes.passes", "call")
    _wire_handler(registry, "statusline", "statusline.statusline", "call")

    # ── Review sub-module ──────────────────────────────────
    _wire_handler(registry, "review", "review.review", "call")

    # ── Rate & Release ─────────────────────────────────────
    _wire_handler(registry, "rate-limit-options", "rate_limit_options.rate_limit_options", "call")
    _wire_handler(registry, "release-notes", "release_notes.release_notes", "call")

    # ── Debug / Internal tools ─────────────────────────────
    return registry


def _wire_handler(registry: CommandRegistry, cmd_name: str, module_path: str, fn_name: str):
    """Lazily wire a handler to a command."""
    import importlib

    def _loader():
        mod = importlib.import_module(f".{module_path}", package="vivian_cli.commands")
        return getattr(mod, fn_name)

    registry.register_handler(cmd_name, _loader)
