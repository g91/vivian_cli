"""Tree rendering — mirrors src/utils/treeify.ts"""
from __future__ import annotations

from typing import Dict, Optional, Union

TreeNode = Dict[str, Union["TreeNode", str, None]]

_BRANCH = "\u251c"      # ├
_LAST_BRANCH = "\u2514" # └
_LINE = "\u2502"        # │
_EMPTY = " "


def treeify(
    obj: TreeNode,
    *,
    show_values: bool = True,
    hide_functions: bool = False,
) -> str:
    """Render a nested dict as an ASCII/Unicode tree string.

    Mirrors treeify() from treeify.ts (without colour/theme support).
    """
    lines: list[str] = []
    visited: set[int] = set()

    def _grow(node, prefix: str, depth: int) -> None:
        if isinstance(node, str):
            lines.append(prefix + node)
            return
        if not isinstance(node, dict) or node is None:
            if show_values:
                lines.append(prefix + str(node))
            return
        nid = id(node)
        if nid in visited:
            lines.append(prefix + "[Circular]")
            return
        visited.add(nid)
        keys = [k for k in node if not (hide_functions and callable(node[k]))]
        for i, key in enumerate(keys):
            value = node[key]
            is_last = i == len(keys) - 1
            node_prefix = "" if (depth == 0 and i == 0) else prefix
            tree_char = _LAST_BRANCH if is_last else _BRANCH
            colored_key = key.strip()
            line = node_prefix + tree_char + (" " + colored_key if colored_key else "")
            should_colon = key.strip() != ""
            if value and isinstance(value, dict):
                if id(value) in visited:
                    lines.append(line + (": " if should_colon else " ") + "[Circular]")
                else:
                    lines.append(line)
                    cont = _EMPTY if is_last else _LINE
                    _grow(value, node_prefix + cont + " ", depth + 1)
            elif isinstance(value, list):
                lines.append(line + (": " if should_colon else " ") + f"[Array({len(value)})]")
            elif show_values:
                val_str = str(value) if not callable(value) else "[Function]"
                sep = ": " if should_colon else (" " if line else "")
                lines.append(line + sep + val_str)
            else:
                lines.append(line)
        visited.discard(nid)

    keys = list(obj.keys())
    if not keys:
        return "(empty)"

    # Special case: single whitespace key with a string value
    if (
        len(keys) == 1
        and keys[0].strip() == ""
        and isinstance(obj.get(keys[0]), str)
    ):
        return _LAST_BRANCH + " " + (obj[keys[0]] or "")

    _grow(obj, "", 0)
    return "\n".join(lines)
