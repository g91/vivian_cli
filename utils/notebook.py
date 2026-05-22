"""Port of src/utils/notebook.ts"""
from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional

LARGE_OUTPUT_THRESHOLD = 10000

BASH_TOOL_NAME = "Bash"


def _process_output_text(text):
    if not text:
        return ""
    raw = "".join(text) if isinstance(text, list) else text
    # Truncate if too long
    if len(raw) > 10000:
        raw = raw[:10000] + "... [truncated]"
    return raw


def _extract_image(data):
    if isinstance(data, dict):
        if isinstance(data.get("image/png"), str):
            return {"image_data": data["image/png"].replace(" ", "").replace("\n", ""), "media_type": "image/png"}
        if isinstance(data.get("image/jpeg"), str):
            return {"image_data": data["image/jpeg"].replace(" ", "").replace("\n", ""), "media_type": "image/jpeg"}
    return None


def _process_output(output):
    t = output.get("output_type")
    if t == "stream":
        return {"output_type": t, "text": _process_output_text(output.get("text"))}
    elif t in ("execute_result", "display_data"):
        data = output.get("data", {})
        return {
            "output_type": t,
            "text": _process_output_text(data.get("text/plain")),
            "image": _extract_image(data),
        }
    elif t == "error":
        tb = output.get("traceback", [])
        return {
            "output_type": t,
            "text": _process_output_text(
                f"{output.get('ename', 'Error')}: {output.get('evalue', '')}\n" + "\n".join(tb)
            ),
        }
    return {"output_type": t}


def _is_large_outputs(outputs):
    size = 0
    for o in outputs:
        if not o:
            continue
        size += len(o.get("text") or "") + len((o.get("image") or {}).get("image_data") or "")
        if size > LARGE_OUTPUT_THRESHOLD:
            return True
    return False


def _process_cell(cell, index, code_language, include_large_outputs):
    cell_id = cell.get("id") or f"cell-{index}"
    source = cell.get("source", "")
    if isinstance(source, list):
        source = "".join(source)
    cell_data = {
        "cellType": cell.get("cell_type"),
        "source": source,
        "cell_id": cell_id,
    }
    if cell.get("cell_type") == "code":
        cell_data["language"] = code_language
        cell_data["execution_count"] = cell.get("execution_count")
        raw_outputs = cell.get("outputs", [])
        if raw_outputs:
            outputs = [_process_output(o) for o in raw_outputs]
            if not include_large_outputs and _is_large_outputs(outputs):
                cell_data["outputs"] = [{
                    "output_type": "stream",
                    "text": f"Outputs are too large to include. Use {BASH_TOOL_NAME} with: cat <notebook_path> | jq '.cells[{index}].outputs'"
                }]
            else:
                cell_data["outputs"] = outputs
    return cell_data


def _cell_content_to_tool_result(cell):
    metadata = []
    if cell.get("cellType") != "code":
        metadata.append(f"<cell_type>{cell.get('cellType')}</cell_type>")
    if cell.get("language") != "python" and cell.get("cellType") == "code":
        metadata.append(f"<language>{cell.get('language')}</language>")
    cid = cell.get("cell_id", "")
    content = f"<cell id=\"{cid}\">{"".join(metadata)}{cell.get('source', '')}</cell id=\"{cid}\">"
    return {"text": content, "type": "text"}


def _cell_output_to_tool_result(output):
    results = []
    if output.get("text"):
        results.append({"text": f"\n{output['text']}", "type": "text"})
    if output.get("image"):
        img = output["image"]
        results.append({"type": "image", "source": {"data": img["image_data"], "media_type": img["media_type"], "type": "base64"}})
    return results


def _get_tool_result_from_cell(cell):
    content = _cell_content_to_tool_result(cell)
    outputs = []
    for o in (cell.get("outputs") or []):
        outputs.extend(_cell_output_to_tool_result(o))
    return [content] + outputs


async def readNotebook(notebook_path, cell_id=None):
    """Reads and parses a Jupyter notebook file into processed cell data."""
    from vivian_cli.utils.path import expandPath
    full_path = expandPath(notebook_path)
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()
    notebook = json.loads(content)
    language = (notebook.get("metadata", {}).get("language_info") or {}).get("name") or "python"
    if cell_id:
        cell = next((c for c in notebook["cells"] if c.get("id") == cell_id), None)
        if not cell:
            raise ValueError(f'Cell with ID "{cell_id}" not found in notebook')
        idx = notebook["cells"].index(cell)
        return [_process_cell(cell, idx, language, True)]
    return [_process_cell(c, i, language, False) for i, c in enumerate(notebook["cells"])]


def mapNotebookCellsToToolResult(data, tool_use_id):
    """Maps notebook cell data to tool result block parameters."""
    all_results = []
    for cell in data:
        all_results.extend(_get_tool_result_from_cell(cell))
    # Merge adjacent text blocks
    merged = []
    for item in all_results:
        if merged and merged[-1]["type"] == "text" and item["type"] == "text":
            merged[-1]["text"] += "\n" + item["text"]
        else:
            merged.append(dict(item))
    return {"tool_use_id": tool_use_id, "type": "tool_result", "content": merged}


def parseCellId(cell_id):
    import re
    m = re.match(r"^cell-(\d+)$", cell_id)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None
