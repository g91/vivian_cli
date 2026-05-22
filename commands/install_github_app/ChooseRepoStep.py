"""ChooseRepoStep — mirrors src/commands/install-github-app/ChooseRepoStep.tsx."""
from __future__ import annotations

def validate_repo_choice(
    current_repo: str | None,
    use_current_repo: bool,
    repo_url: str,
) -> tuple[bool, str | None]:
    repo_name = current_repo if use_current_repo else repo_url
    if not repo_name or not repo_name.strip():
        return False, "Please enter a repository name to continue"
    return True, None


def render_choose_repo_step(
    current_repo: str | None,
    use_current_repo: bool,
    repo_url: str,
    show_empty_error: bool = False,
) -> dict:
    _, error = validate_repo_choice(current_repo, use_current_repo, repo_url)
    return {
        "title": "Install GitHub App",
        "subtitle": "Select GitHub repository",
        "options": [
            {
                "id": "current",
                "label": f"Use current repository: {current_repo}",
                "selected": bool(current_repo and use_current_repo),
                "visible": bool(current_repo),
            },
            {
                "id": "manual",
                "label": "Enter a different repository" if current_repo else "Enter repository",
                "selected": not use_current_repo or not current_repo,
                "visible": True,
            },
        ],
        "input": {
            "visible": not use_current_repo or not current_repo,
            "value": repo_url,
            "placeholder": "Enter a repo as owner/repo or https://github.com/owner/repo…",
        },
        "error": error if show_empty_error else None,
        "navigation_hint": ("up/down to select · " if current_repo else "") + "Enter to continue",
    }


choose_repo_step = render_choose_repo_step
