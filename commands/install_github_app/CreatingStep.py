"""CreatingStep — mirrors src/commands/install-github-app/CreatingStep.tsx."""
from __future__ import annotations

def get_progress_steps(
    secret_exists: bool,
    use_existing_secret: bool,
    secret_name: str,
    skip_workflow: bool = False,
    selected_workflows: list[str] | None = None,
) -> list[str]:
    selected_workflows = selected_workflows or []
    secret_step = (
        "Using existing API key secret"
        if secret_exists and use_existing_secret
        else f"Setting up {secret_name} secret"
    )
    if skip_workflow:
        return ["Getting repository information", secret_step]
    workflow_step = "Creating workflow files" if len(selected_workflows) > 1 else "Creating workflow file"
    return [
        "Getting repository information",
        "Creating branch",
        workflow_step,
        secret_step,
        "Opening pull request page",
    ]


def render_creating_step(
    current_workflow_install_step: int,
    secret_exists: bool,
    use_existing_secret: bool,
    secret_name: str,
    skip_workflow: bool = False,
    selected_workflows: list[str] | None = None,
) -> dict:
    steps = get_progress_steps(
        secret_exists,
        use_existing_secret,
        secret_name,
        skip_workflow,
        selected_workflows,
    )
    return {
        "title": "Install GitHub App",
        "subtitle": "Create GitHub Actions workflow",
        "steps": [
            {
                "text": step_text,
                "status": (
                    "completed"
                    if index < current_workflow_install_step
                    else "in-progress"
                    if index == current_workflow_install_step
                    else "pending"
                ),
            }
            for index, step_text in enumerate(steps)
        ],
    }


creating_step = render_creating_step
