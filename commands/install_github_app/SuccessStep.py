"""SuccessStep — mirrors src/commands/install-github-app/SuccessStep.tsx."""
from __future__ import annotations

def render_success_step(
    secret_exists: bool,
    use_existing_secret: bool,
    secret_name: str,
    skip_workflow: bool = False,
) -> dict:
    next_steps = (
        [
            "Install the vivian GitHub App if you haven't already",
            "Your workflow file was kept unchanged",
            "API key is configured and ready to use",
        ]
        if skip_workflow
        else [
            "A pre-filled PR page has been created",
            "Install the vivian GitHub App if you haven't already",
            "Merge the PR to enable vivian PR assistance",
        ]
    )
    return {
        "title": "Install GitHub App",
        "subtitle": "Success",
        "workflow_created": not skip_workflow,
        "used_existing_secret": secret_exists and use_existing_secret,
        "saved_secret": (not secret_exists) or (not use_existing_secret),
        "secret_name": secret_name,
        "next_steps": next_steps,
        "footer": "Press any key to exit",
    }


success_step = render_success_step
