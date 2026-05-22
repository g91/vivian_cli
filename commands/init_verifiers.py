"""init-verifiers command — mirrors src/commands/init-verifiers.ts.

Creates verifier skill(s) for automated verification of code changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult

VERIFIER_PROMPT = """Analyze this project and create verifier skills that can automatically verify code changes.

A verifier skill should:
1. Define what to check (linting, tests, type checking, formatting, etc.)
2. Specify the commands to run for verification
3. Describe what success/failure looks like

Create verifier skills for:
- Build verification (does the project compile/build?)
- Test verification (do tests pass?)
- Lint verification (does the code follow style guides?)
- Type verification (are types correct?)

For each verifier, provide:
- Name and description
- The exact commands to run
- How to interpret the output"""


async def call(args: str, context: CommandContext) -> TextResult:
    from ..types.command import TextResult
    return TextResult(VERIFIER_PROMPT)


initVerifiers = call
init_verifiers = call
