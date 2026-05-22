"""ExitWorktreeTool prompt — mirrors src/tools/ExitWorktreeTool/prompt.ts"""
EXIT_WORKTREE_TOOL_NAME = "ExitWorktree"

DESCRIPTION = "Exit the current git worktree and clean up"

EXIT_WORKTREE_PROMPT = """Use this tool to exit the current git worktree.
This will:
1. Commit or discard changes (based on your preference)
2. Remove the worktree directory
3. Return to the main working directory

Make sure to save any important changes before exiting."""
