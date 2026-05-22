"""EnterPlanModeTool prompt — mirrors src/tools/EnterPlanModeTool/prompt.ts"""
ENTER_PLAN_MODE_TOOL_NAME = "EnterPlanMode"

DESCRIPTION = "Enter plan mode to create a detailed plan before implementing changes"

ENTER_PLAN_MODE_PROMPT = """Use this tool to enter plan mode. In plan mode, you will:
1. Analyze the user's request thoroughly
2. Create a detailed step-by-step plan
3. Present the plan to the user for approval
4. Only begin implementation after the user approves the plan

This is useful for complex multi-step tasks where careful planning reduces errors."""
