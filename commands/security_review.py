"""security-review command — mirrors src/commands/security-review.ts.

Security-focused code review of pending changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult

SECURITY_REVIEW_PROMPT = """You are a security expert. Review the pending changes for security issues.

!`git diff HEAD`

Analyze for:
1. **Injection vulnerabilities** — SQL, command, code injection risks
2. **Authentication/Authorization** — Proper access controls
3. **Data exposure** — Sensitive data leaks, logging secrets
4. **Input validation** — Untrusted input handling
5. **Cryptography** — Weak algorithms, hardcoded keys
6. **Dependencies** — Known vulnerable packages
7. **Configuration** — Security misconfigurations

For each finding, provide:
- Severity (Critical/High/Medium/Low)
- Description of the issue
- Location (file and line)
- Recommended fix"""


async def call(args: str, context: CommandContext) -> TextResult:
    from ..types.command import TextResult
    return TextResult(SECURITY_REVIEW_PROMPT)


securityReview = call
security_review = call
