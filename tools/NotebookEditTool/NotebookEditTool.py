"""NotebookEditTool — mirrors src/tools/NotebookEditTool/NotebookEditTool.tsx"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional

TOOL_NAME = "NotebookEdit"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["notebook_path", "cell_id"],
    "properties": {
        "notebook_path": {"type": "string", "description": "Path to the Jupyter notebook"},
        "cell_id": {"type": "string", "description": "Cell ID or index to edit"},
        "source": {"type": "string", "description": "New source content for the cell"},
        "cell_type": {"type": "string", "enum": ["code", "markdown"], "description": "Cell type"},
    },
}


async def description() -> str:
    return "Edit a cell in a Jupyter notebook."


async def prompt() -> str:
    return (
        "Use this tool to edit a specific cell in a Jupyter notebook. "
        "Specify the notebook path, cell ID, and new source content."
    )


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    notebook_path = input_data.get("notebook_path", "")
    cell_id = input_data.get("cell_id", "")
    source = input_data.get("source", "")

    path = Path(notebook_path)
    if not path.exists():
        return {"error": f"Notebook not found: {notebook_path}"}

    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {"error": str(e)}

    cells = nb.get("cells", [])
    # Find by id or index
    target = None
    for i, cell in enumerate(cells):
        if cell.get("id") == cell_id or str(i) == str(cell_id):
            target = cell
            break

    if target is None:
        return {"error": f"Cell not found: {cell_id}"}

    target["source"] = source.splitlines(keepends=True)

    try:
        path.write_text(json.dumps(nb, indent=1), encoding="utf-8")
        return {"success": True, "cell_id": cell_id}
    except OSError as e:
        return {"error": str(e)}
