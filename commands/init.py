"""init command — mirrors src/commands/init.ts.

Analyzes the codebase and creates/improves a vivian.md file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult

INIT_PROMPT = """Please analyze this codebase and create a vivian.md file, which will be given to future instances of Vivian AI to operate in this repository.

What to add:
1. Commands that will be commonly used, such as how to build, lint, and run tests. Include the necessary commands to develop in this codebase, such as how to run a single test.
2. High-level code architecture and structure so that future instances can be productive more quickly. Focus on the "big picture" architecture that requires reading multiple files to understand.

Usage notes:
- If there's already a vivian.md, suggest improvements to it.
- When you make the initial vivian.md, do not repeat yourself and do not include obvious instructions like "Provide helpful error messages to users", "Write unit tests for all new utilities", "Never include sensitive information (API keys, tokens) in code or commits".
- Avoid listing every component or file structure that can be easily discovered.
- Don't include generic development practices.
- If there are Cursor rules (in .cursor/rules/ or .cursorrules) or Copilot rules (in .github/copilot-instructions.md), make sure to include the important parts.
- If there is a README.md, make sure to include the important parts.
- Do not make up information such as "Common Development Tasks", "Tips for Development", "Support and Documentation" unless this is expressly included in other files that you read.
- Be sure to prefix the file with the following text:

```
# vivian.md

This file provides guidance to Vivian AI (api-vivian.d0a.net/code) when working with code in this repository.
```"""


async def call(args: str, context: CommandContext) -> TextResult:
    """Initialize project vivian.md."""
    from ..types.command import TextResult
    return TextResult(INIT_PROMPT)


initProject = call
init_project = call
