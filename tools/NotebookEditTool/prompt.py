"""NotebookEditTool prompt — mirrors src/tools/NotebookEditTool/prompt.ts"""
NOTEBOOK_EDIT_TOOL_NAME = "NotebookEdit"

DESCRIPTION = "Edit a Jupyter Notebook cell"

NOTEBOOK_EDIT_PROMPT = """Use this tool to edit cells in Jupyter Notebooks (.ipynb files).
You can:
1. Insert new cells (code or markdown)
2. Edit existing cells
3. Delete cells

Specify the cell by its ID or position."""
