"""TodoWriteTool prompt — mirrors src/tools/TodoWriteTool/prompt.ts"""
TODO_WRITE_TOOL_NAME = "TodoWrite"

DESCRIPTION = "Create and manage a structured task list"

TODO_WRITE_PROMPT = """Use this tool to create and manage a structured task list for your current coding session.
This helps track progress, organize complex tasks, and demonstrate thoroughness.

Note: Other than when first creating todos, don't tell the user you're updating todos, just do it.

### When to Use This Tool
Use proactively for:
1. Complex multi-step tasks (3+ distinct steps)
2. Non-trivial tasks requiring careful planning
3. User explicitly requests todo list
4. User provides multiple tasks (numbered/comma-separated)
5. After receiving new instructions - capture requirements as todos
6. **IMPORTANT: When you START working on a task** - mark it as in-progress
7. **IMPORTANT: IMMEDIATELY after COMPLETING a task** - mark it as completed

Todo items guidelines:
- Todo list should be clear, executable, and oriented toward user-facing functional modules
- Each item must represent a meaningful unit of work, focusing on complete functional modules that are user-visible and interactive
- Avoid overly granular tasks that consist of single trivial actions
- Avoid technical implementation details such as "set up project structure," "add responsive design," or "configure webpack." Think from the user's perspective: what features will they see and use
- When spec exist and spec status is building, using spec todos as the todo list
- Important: The todo list should preferably contain no more than 7 items unless spec exist and spec's todos more than 7 items

### When NOT to Use
Skip for:
1. Single, trivial tasks
2. Trivial tasks with no organizational benefit
3. Tasks completable in < 3 trivial steps
4. Purely conversational/informational requests
5. Todo items should NOT include operational actions done in service of higher-level tasks

NEVER INCLUDE THESE IN TODOS: linting; testing; searching or examining the codebase

### Examples

<example>
  User: Add dark mode toggle to settings
  Assistant:
    - *Creates todo list:*
      1. Add state management [in-progress]
      2. Implement styles
      3. Create toggle component
      4. Update components
    - [Immediately begins working on todo 1 in the same tool call batch]
<reasoning>
  Multi-step feature with dependencies.
</reasoning>
</example>

<example>
  User: Rename getCwd to getCurrentWorkingDirectory across my project
  Assistant: *Searches codebase, finds 15 instances across 8 files*
  *Creates todo list with specific items for each file that needs updating*

<reasoning>
  Complex refactoring requiring systematic tracking across multiple files.
</reasoning>
</example>

<example>
  User: Implement user registration, product catalog, shopping cart, checkout flow.
  Assistant: *Creates todo list breaking down each feature into specific tasks*
<reasoning>
  Multiple complex features provided as list requiring organized task management.
</reasoning>
</example>

<example>
  User: Optimize my React app - it's rendering slowly.
  Assistant: *Analyzes codebase, identifies issues*
  *Creates todo list: 1) Memoization, 2) Virtualization, 3) Image optimization, 4) Fix state loops, 5) Code splitting*
<reasoning>
  Performance optimization requires multiple steps across different components.
</reasoning>
</example>

### Examples of When NOT to Use the Todo List
<example>
  User: What does git status do?
  Assistant: Shows current state of working directory and staging area...
<reasoning>
  Informational request with no coding task to complete.
</reasoning>
</example>

<example>
  User: Add comment to calculateTotal function.
  Assistant: *Uses Edit tool to add comment*
<reasoning>
  Single straightforward task in one location.
</reasoning>
</example>

<example>
  User: Run npm install for me.
  Assistant: *Runs npm install* Command completed successfully...
<reasoning>
  Single command execution with immediate results.
</reasoning>
</example>

### Task States and Management
1. **Task States:**
  - pending: Not yet started
  - in-progress: Currently working on (ONLY ONE at a time)
  - completed: Finished successfully
  - cancelled: No longer needed

2. **Task Management:**
  - Update status in real-time - mark complete IMMEDIATELY after finishing
  - Only ONE task in-progress at a time
  - Complete current tasks before starting new ones
  - ALWAYS use the todo list for multi-step tasks

3. **Task Breakdown:**
  - Create specific, actionable items
  - Break complex tasks into manageable steps
  - Use clear, descriptive names

When in doubt, use this tool. Proactive task management demonstrates attentiveness and ensures complete requirements."""
