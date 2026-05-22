"""Keybindings bundled skill — mirrors src/skills/bundled/keybindings.ts."""
from __future__ import annotations

from ..bundled_skills import BundledSkillDefinition, register_bundled_skill
from ...keybindings.defaultBindings import DEFAULT_BINDINGS
from ...keybindings.loadUserBindings import isKeybindingCustomizationEnabled
from ...keybindings.reservedShortcuts import (
  MACOS_RESERVED,
  NON_REBINDABLE,
  TERMINAL_RESERVED,
)
from ...keybindings.schema import (
  KEYBINDING_ACTIONS,
  KEYBINDING_CONTEXTS,
  KEYBINDING_CONTEXT_DESCRIPTIONS,
)
from ...utils.slowOperations import json_stringify


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
  separator = ["---" for _ in headers]
  return "\n".join(
    [
      f"| {' | '.join(headers)} |",
      f"| {' | '.join(separator)} |",
      *[f"| {' | '.join(row)} |" for row in rows],
    ]
  )


def _generate_contexts_table() -> str:
  return _markdown_table(
    ["Context", "Description"],
    [[f"`{ctx}`", KEYBINDING_CONTEXT_DESCRIPTIONS[ctx]] for ctx in KEYBINDING_CONTEXTS],
  )


def _infer_context_from_action(action: str) -> str:
  prefix = action.split(":", 1)[0]
  prefix_to_context = {
    "app": "Global",
    "history": "Global or Chat",
    "chat": "Chat",
    "autocomplete": "Autocomplete",
    "confirm": "Confirmation",
    "tabs": "Tabs",
    "transcript": "Transcript",
    "historySearch": "HistorySearch",
    "task": "Task",
    "theme": "ThemePicker",
    "help": "Help",
    "attachments": "Attachments",
    "footer": "Footer",
    "messageSelector": "MessageSelector",
    "messageActions": "MessageActions",
    "diff": "DiffDialog",
    "modelPicker": "ModelPicker",
    "select": "Select",
    "permission": "Confirmation",
    "settings": "Settings",
    "voice": "Chat",
    "selection": "Scroll",
    "scroll": "Scroll",
    "plugin": "Plugin",
  }
  return prefix_to_context.get(prefix, "Unknown")


def _generate_actions_table() -> str:
  action_info: dict[str, dict[str, str | list[str]]] = {}
  for block in DEFAULT_BINDINGS:
    for key, action in block.bindings.items():
      if action is None:
        continue
      info = action_info.setdefault(action, {"keys": [], "context": block.context})
      info["keys"].append(f"`{key}`")

  rows: list[list[str]] = []
  for action in KEYBINDING_ACTIONS:
    info = action_info.get(action)
    keys = ", ".join(info["keys"]) if info else "(none)"
    context = str(info["context"]) if info else _infer_context_from_action(action)
    rows.append([f"`{action}`", keys, context])
  return _markdown_table(["Action", "Default Key(s)", "Context"], rows)


def _generate_reserved_shortcuts() -> str:
  sections: list[str] = ["### Non-rebindable (errors)"]
  sections.extend(f"- `{item['key']}` — {item['reason']}" for item in NON_REBINDABLE)
  sections.append("")
  sections.append("### Terminal reserved (errors/warnings)")
  sections.extend(
    f"- `{item['key']}` — {item['reason']} ({'will not work' if item['severity'] == 'error' else 'may conflict'})"
    for item in TERMINAL_RESERVED
  )
  sections.append("")
  sections.append("### macOS reserved (errors)")
  sections.extend(f"- `{item['key']}` — {item['reason']}" for item in MACOS_RESERVED)
  return "\n".join(sections)


FILE_FORMAT_EXAMPLE = {
  "$schema": "https://www.schemastore.org/vivian-code-keybindings.json",
  "$docs": "https://api-vivian.d0a.net/docs/en/keybindings",
  "bindings": [
    {
      "context": "Chat",
      "bindings": {"ctrl+e": "chat:externalEditor"},
    }
  ],
}

UNBIND_EXAMPLE = {
  "context": "Chat",
  "bindings": {"ctrl+s": None},
}

REBIND_EXAMPLE = {
  "context": "Chat",
  "bindings": {
    "ctrl+g": None,
    "ctrl+e": "chat:externalEditor",
  },
}

CHORD_EXAMPLE = {
  "context": "Global",
  "bindings": {"ctrl+k ctrl+t": "app:toggleTodos"},
}


def _build_prompt(args: str = "") -> str:
  sections = [
    "# Keybindings Skill",
    "",
    "Create or modify `~/.vivian/keybindings.json` to customize keyboard shortcuts.",
    "",
    "## CRITICAL: Read Before Write",
    "",
    "**Always read `~/.vivian/keybindings.json` first** (it may not exist yet). Merge changes with existing bindings — never replace the entire file.",
    "",
    "- Use Edit for modifications to an existing file",
    "- Use Write only when the file does not exist yet",
    "",
    "## File Format",
    "",
    "```json",
    json_stringify(FILE_FORMAT_EXAMPLE, indent=2),
    "```",
    "",
    "Always include the `$schema` and `$docs` fields.",
    "",
    "## Keystroke Syntax",
    "",
    "- Modifiers: `ctrl`, `alt`/`opt`/`option`, `shift`, `meta`/`cmd`/`command`",
    "- Special keys: `escape`/`esc`, `enter`/`return`, `tab`, `space`, `backspace`, `delete`, `up`, `down`, `left`, `right`",
    "- Chords use spaces between keystrokes, e.g. `ctrl+k ctrl+s`",
    "- Examples: `ctrl+shift+p`, `alt+enter`, `ctrl+k ctrl+n`",
    "",
    "## Unbinding Default Shortcuts",
    "",
    "```json",
    json_stringify(UNBIND_EXAMPLE, indent=2),
    "```",
    "",
    "## Common Patterns",
    "",
    "### Rebind a key",
    "```json",
    json_stringify(REBIND_EXAMPLE, indent=2),
    "```",
    "",
    "### Add a chord binding",
    "```json",
    json_stringify(CHORD_EXAMPLE, indent=2),
    "```",
    "",
    "## Behavioral Rules",
    "",
    "1. Only include contexts the user wants to change.",
    "2. Validate that actions and contexts come from the known lists below.",
    "3. Warn about reserved shortcuts and terminal conflicts before writing.",
    "4. New bindings are additive unless the old binding is explicitly set to `null`.",
    "5. To fully replace a default, unbind the old key and add the new binding.",
    "",
    "## Validation with /doctor",
    "",
    'The `/doctor` command should surface keybinding configuration issues in `~/.vivian/keybindings.json`.',
    "",
    f"## Reserved Shortcuts\n\n{_generate_reserved_shortcuts()}",
    f"## Available Contexts\n\n{_generate_contexts_table()}",
    f"## Available Actions\n\n{_generate_actions_table()}",
  ]
  if args:
    sections.extend(["", "## User Request", "", args])
  return "\n".join(sections)


def register_keybindings_skill() -> None:
  register_bundled_skill(
    BundledSkillDefinition(
      name="keybindings",
      description="Use when the user wants to customize keyboard shortcuts or modify ~/.vivian/keybindings.json.",
      allowed_tools=["Read"],
      user_invocable=False,
      is_enabled=isKeybindingCustomizationEnabled,
      get_prompt_for_command=lambda args="", ctx=None: [
        {"type": "text", "text": _build_prompt(args)}
      ],
    )
  )
