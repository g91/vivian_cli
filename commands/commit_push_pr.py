"""commit-push-pr command — mirrors src/commands/commit-push-pr.ts.

Commits all changes, pushes to origin, and creates/updates a pull request.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult

ALLOWED_TOOLS = [
    "Bash(git checkout --branch:*)",
    "Bash(git checkout -b:*)",
    "Bash(git add:*)",
    "Bash(git status:*)",
    "Bash(git push:*)",
    "Bash(git commit:*)",
    "Bash(gh pr create:*)",
    "Bash(gh pr edit:*)",
    "Bash(gh pr view:*)",
    "Bash(gh pr merge:*)",
]


def getPromptContent(default_branch: str = "main", pr_attribution: str = "") -> str:
    """Build the commit-push-pr prompt."""
    import os
    safe_user = os.environ.get("SAFEUSER", "")
    username = os.environ.get("USER", "")

    return f"""## Context

- `SAFEUSER`: {safe_user}
- `whoami`: {username}
- `git status`: !`git status`
- `git diff HEAD`: !`git diff HEAD`
- `git branch --show-current`: !`git branch --show-current`
- `git diff {default_branch}...HEAD`: !`git diff {default_branch}...HEAD`
- `gh pr view --json number 2>/dev/null || true`: !`gh pr view --json number 2>/dev/null || true`

## Git Safety Protocol

- NEVER update the git config
- NEVER run destructive/irreversible git commands (like push --force, hard reset, etc) unless the user explicitly requests them
- NEVER skip hooks (--no-verify, --no-gpg-sign, etc) unless the user explicitly requests it
- NEVER run force push to main/master, warn the user if they request it
- Do not commit files that likely contain secrets (.env, credentials.json, etc)
- Never use git commands with the -i flag (like git rebase -i or git add -i) since they require interactive input which is not supported

## Your task

Analyze all changes that will be included in the pull request, making sure to look at all relevant commits (NOT just the latest commit, but ALL commits that will be included in the pull request from the git diff {default_branch}...HEAD output above).

Based on the above changes:
1. Create a new branch if on {default_branch} (use SAFEUSER from context above for the branch name prefix, falling back to whoami if SAFEUSER is empty, e.g., `username/feature-name`)
2. Create a single commit with an appropriate message using heredoc syntax:
```
git commit -m "$(cat <<'EOF'
Commit message here.{f'{chr(10)}{chr(10)}{pr_attribution}' if pr_attribution else ''}
EOF
)"
```
3. Push the branch to origin
4. If a PR already exists for this branch (check the gh pr view output above), update the PR title and body using `gh pr edit` to reflect the current diff. Otherwise, create a pull request using `gh pr create` with heredoc syntax for the body.
   - IMPORTANT: Keep PR titles short (under 70 characters). Use the body for details.
```
gh pr create --title "Short, descriptive title" --body "$(cat <<'EOF'
## Summary
<1-3 bullet points>

## Test plan
[Bulleted markdown checklist of TODOs for testing the pull request...]
{'## Changelog' + chr(10) + '<!-- CHANGELOG:START -->' + chr(10) + '[If this PR contains user-facing changes, add a changelog entry here. Otherwise, remove this section.]' + chr(10) + '<!-- CHANGELOG:END -->' + chr(10)}{f'{chr(10)}{chr(10)}{pr_attribution}' if pr_attribution else ''}
EOF
)"
```

You have the capability to call multiple tools in a single response. You MUST do all of the above in a single message.

Return the PR URL when you're done, so the user can see it."""


async def call(args: str, context: CommandContext) -> TextResult:
    """Generate commit-push-pr prompt."""
    from ..types.command import TextResult
    from ..utils.attribution import getAttributionTexts, getEnhancedPRAttribution
    from ..utils.git import get_default_branch

    default_branch = await get_default_branch()
    app_state_getter = None
    engine = getattr(context, 'engine', None)
    if engine is not None and hasattr(engine, 'state_store'):
        app_state_getter = lambda: engine.state_store.get_state()

    default_texts = getAttributionTexts() or {}
    enhanced_pr_attribution = await getEnhancedPRAttribution(app_state_getter)
    effective_pr_attribution = enhanced_pr_attribution or default_texts.get('pr', '')

    prompt = getPromptContent(default_branch or "main", effective_pr_attribution)
    if args.strip():
        prompt += f"\n\n## Additional instructions from user\n\n{args.strip()}"
    return TextResult(value=prompt)


commitPushPR = call
commit_push_pr = call
get_prompt_content = getPromptContent
