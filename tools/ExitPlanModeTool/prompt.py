"""ExitPlanModeTool prompt — mirrors src/tools/ExitPlanModeTool/prompt.ts"""
EXIT_PLAN_MODE_TOOL_NAME = "ExitPlanMode"

DESCRIPTION = "Exit plan mode and present the plan for approval"

EXIT_PLAN_MODE_PROMPT = """Use this tool to exit plan mode and present your plan to the user.
Include a detailed step-by-step plan that covers:
1. What files will be created/modified/deleted
2. The order of operations
3. Key design decisions and trade-offs
4. Testing strategy

The user will review and either approve the plan or request changes."""
