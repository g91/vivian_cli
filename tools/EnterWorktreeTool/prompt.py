"""EnterWorktreeTool prompt — mirrors src/tools/EnterWorktreeTool/prompt.ts"""
ENTER_WORKTREE_TOOL_NAME = "EnterWorktree"

DESCRIPTION = "Enter a git worktree for isolated work"

ENTER_WORKTREE_PROMPT = """Use this tool to create and enter a git worktree. Worktrees allow you to:
1. Work on multiple branches simultaneously
2. Isolate changes from your main working directory
3. Switch contexts without stashing or committing

The worktree will be created in a temporary location and cleaned up when you exit."""
