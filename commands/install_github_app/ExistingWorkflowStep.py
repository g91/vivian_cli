"""ExistingWorkflowStep — mirrors src/commands/install-github-app/ExistingWorkflowStep.tsx."""
from __future__ import annotations

EXISTING_WORKFLOW_OPTIONS = [
    {"label": "Update workflow file with latest version", "value": "update"},
    {"label": "Skip workflow update (configure secrets only)", "value": "skip"},
    {"label": "Exit without making changes", "value": "exit"},
]


def render_existing_workflow_step(repo_name: str) -> dict:
    return {
        "title": "Existing Workflow Found",
        "repository": repo_name,
        "message": "A vivian workflow file already exists at .github/workflows/vivian.yml",
        "prompt": "What would you like to do?",
        "options": EXISTING_WORKFLOW_OPTIONS,
        "template_url": "https://github.com/anthropics/vivian-code-action/blob/main/examples/vivian.yml",
    }


existing_workflow_step = render_existing_workflow_step
