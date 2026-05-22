"""Port of src/ink/optimizer.ts."""
from __future__ import annotations

from typing import Any

Diff = list[dict[str, Any]]


def optimize(diff: Diff) -> Diff:
    if len(diff) <= 1:
        return diff

    result: Diff = []
    length = 0

    for patch in diff:
        t = patch["type"]

        if t == "stdout" and patch.get("content") == "":
            continue
        if t == "cursorMove" and patch.get("x") == 0 and patch.get("y") == 0:
            continue
        if t == "clear" and patch.get("count") == 0:
            continue

        if length > 0:
            last = result[length - 1]
            lt = last["type"]

            if t == "cursorMove" and lt == "cursorMove":
                result[length - 1] = {
                    "type": "cursorMove",
                    "x": last["x"] + patch["x"],
                    "y": last["y"] + patch["y"],
                }
                continue

            if t == "cursorTo" and lt == "cursorTo":
                result[length - 1] = patch
                continue

            if t == "styleStr" and lt == "styleStr":
                result[length - 1] = {"type": "styleStr", "str": last["str"] + patch["str"]}
                continue

            if t == "hyperlink" and lt == "hyperlink" and patch.get("uri") == last.get("uri"):
                continue

            if (t == "cursorShow" and lt == "cursorHide") or (t == "cursorHide" and lt == "cursorShow"):
                result.pop()
                length -= 1
                continue

        result.append(patch)
        length += 1

    return result
