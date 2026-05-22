"""setupGitHubActions — mirrors src/commands/install-github-app/setupGitHubActions.ts."""
from __future__ import annotations

import base64
import logging
import time
from collections.abc import Callable
from urllib.parse import quote

from ...constants.github_app import (
    CODE_REVIEW_PLUGIN_WORKFLOW_CONTENT,
    PR_BODY,
    PR_TITLE,
    WORKFLOW_CONTENT,
)
from ...services.analytics.index import log_event
from ...utils.browser import open_browser
from ...utils.config import save_global_config
from ...utils.execFileNoThrow import exec_file_no_throw


WorkflowName = str


def _result_code(result: dict) -> int:
    return int(result.get("code", -1))


def _result_stdout(result: dict) -> str:
    return str(result.get("stdout", ""))


def _result_stderr(result: dict) -> str:
    return str(result.get("stderr", ""))


async def create_workflow_file(
    repo_name: str,
    branch_name: str,
    workflow_path: str,
    workflow_content: str,
    secret_name: str,
    message: str,
    context: dict | None = None,
) -> None:
    context = context or {}
    check_file_result = await exec_file_no_throw(
        "gh",
        ["api", f"repos/{repo_name}/contents/{workflow_path}", "--jq", ".sha"],
    )

    file_sha: str | None = None
    if _result_code(check_file_result) == 0:
        file_sha = _result_stdout(check_file_result).strip()

    content = workflow_content
    if secret_name == "vivian_CODE_OAUTH_TOKEN":
        content = content.replace(
            "anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}",
            "vivian_code_oauth_token: ${{ secrets.vivian_CODE_OAUTH_TOKEN }}",
        )
    elif secret_name != "ANTHROPIC_API_KEY":
        content = content.replace(
            "anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}",
            f"anthropic_api_key: ${{{{ secrets.{secret_name} }}}}",
        )

    base64_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
    api_params = [
        "api",
        "--method",
        "PUT",
        f"repos/{repo_name}/contents/{workflow_path}",
        "-f",
        f'message={"Update " + message if file_sha else message}',
        "-f",
        f"content={base64_content}",
        "-f",
        f"branch={branch_name}",
    ]
    if file_sha:
        api_params.extend(["-f", f"sha={file_sha}"])

    create_file_result = await exec_file_no_throw("gh", api_params)
    if _result_code(create_file_result) == 0:
        return

    stderr = _result_stderr(create_file_result)
    if "422" in stderr and "sha" in stderr:
        log_event(
            "tengu_setup_github_actions_failed",
            {
                "reason": "failed_to_create_workflow_file",
                "exit_code": _result_code(create_file_result),
                **context,
            },
        )
        raise RuntimeError(
            f"Failed to create workflow file {workflow_path}: "
            "A vivian workflow file already exists in this repository. Please remove it first or update it manually."
        )

    log_event(
        "tengu_setup_github_actions_failed",
        {
            "reason": "failed_to_create_workflow_file",
            "exit_code": _result_code(create_file_result),
            **context,
        },
    )
    help_text = (
        "\n\nNeed help? Common issues:\n"
        "· Permission denied → Run: gh auth refresh -h github.com -s repo,workflow\n"
        "· Not authorized → Ensure you have admin access to the repository\n"
        "· For manual setup → Visit: https://github.com/anthropics/vivian-code-action"
    )
    raise RuntimeError(
        f"Failed to create workflow file {workflow_path}: {stderr}{help_text}"
    )


async def setup_github_actions(
    repo_name: str,
    api_key_or_oauth_token: str | None,
    secret_name: str,
    update_progress: Callable[[], None],
    skip_workflow: bool = False,
    selected_workflows: list[WorkflowName] | None = None,
    auth_type: str = "api_key",
    context: dict | None = None,
) -> None:
    context = context or {}
    selected_workflows = selected_workflows or []

    try:
        log_event(
            "tengu_setup_github_actions_started",
            {
                "skip_workflow": skip_workflow,
                "has_api_key": bool(api_key_or_oauth_token),
                "using_default_secret_name": secret_name == "ANTHROPIC_API_KEY",
                "selected_vivian_workflow": "vivian" in selected_workflows,
                "selected_vivian_review_workflow": "vivian-review" in selected_workflows,
                **context,
            },
        )

        repo_check_result = await exec_file_no_throw(
            "gh", ["api", f"repos/{repo_name}", "--jq", ".id"]
        )
        if _result_code(repo_check_result) != 0:
            log_event(
                "tengu_setup_github_actions_failed",
                {
                    "reason": "repo_not_found",
                    "exit_code": _result_code(repo_check_result),
                    **context,
                },
            )
            raise RuntimeError(
                f"Failed to access repository {repo_name}: {_result_stderr(repo_check_result)}"
            )

        default_branch_result = await exec_file_no_throw(
            "gh", ["api", f"repos/{repo_name}", "--jq", ".default_branch"]
        )
        if _result_code(default_branch_result) != 0:
            log_event(
                "tengu_setup_github_actions_failed",
                {
                    "reason": "failed_to_get_default_branch",
                    "exit_code": _result_code(default_branch_result),
                    **context,
                },
            )
            raise RuntimeError(
                f"Failed to get default branch: {_result_stderr(default_branch_result)}"
            )
        default_branch = _result_stdout(default_branch_result).strip()

        sha_result = await exec_file_no_throw(
            "gh",
            ["api", f"repos/{repo_name}/git/ref/heads/{default_branch}", "--jq", ".object.sha"],
        )
        if _result_code(sha_result) != 0:
            log_event(
                "tengu_setup_github_actions_failed",
                {
                    "reason": "failed_to_get_branch_sha",
                    "exit_code": _result_code(sha_result),
                    **context,
                },
            )
            raise RuntimeError(f"Failed to get branch SHA: {_result_stderr(sha_result)}")
        sha = _result_stdout(sha_result).strip()

        branch_name: str | None = None
        if not skip_workflow:
            update_progress()
            branch_name = f"add-vivian-github-actions-{int(time.time() * 1000)}"
            create_branch_result = await exec_file_no_throw(
                "gh",
                [
                    "api",
                    "--method",
                    "POST",
                    f"repos/{repo_name}/git/refs",
                    "-f",
                    f"ref=refs/heads/{branch_name}",
                    "-f",
                    f"sha={sha}",
                ],
            )
            if _result_code(create_branch_result) != 0:
                log_event(
                    "tengu_setup_github_actions_failed",
                    {
                        "reason": "failed_to_create_branch",
                        "exit_code": _result_code(create_branch_result),
                        **context,
                    },
                )
                raise RuntimeError(
                    f"Failed to create branch: {_result_stderr(create_branch_result)}"
                )

            update_progress()
            workflows: list[tuple[str, str, str]] = []
            if "vivian" in selected_workflows:
                workflows.append(
                    (
                        ".github/workflows/vivian.yml",
                        WORKFLOW_CONTENT,
                        "vivian PR Assistant workflow",
                    )
                )
            if "vivian-review" in selected_workflows:
                workflows.append(
                    (
                        ".github/workflows/vivian-code-review.yml",
                        CODE_REVIEW_PLUGIN_WORKFLOW_CONTENT,
                        "vivian Code Review workflow",
                    )
                )

            for workflow_path, workflow_content, message in workflows:
                await create_workflow_file(
                    repo_name,
                    branch_name,
                    workflow_path,
                    workflow_content,
                    secret_name,
                    message,
                    context,
                )

        update_progress()
        if api_key_or_oauth_token:
            set_secret_result = await exec_file_no_throw(
                "gh",
                [
                    "secret",
                    "set",
                    secret_name,
                    "--body",
                    api_key_or_oauth_token,
                    "--repo",
                    repo_name,
                ],
            )
            if _result_code(set_secret_result) != 0:
                log_event(
                    "tengu_setup_github_actions_failed",
                    {
                        "reason": "failed_to_set_api_key_secret",
                        "exit_code": _result_code(set_secret_result),
                        **context,
                    },
                )
                help_text = (
                    "\n\nNeed help? Common issues:\n"
                    "· Permission denied → Run: gh auth refresh -h github.com -s repo\n"
                    "· Not authorized → Ensure you have admin access to the repository\n"
                    "· For manual setup → Visit: https://github.com/anthropics/vivian-code-action"
                )
                stderr = _result_stderr(set_secret_result) or "Unknown error"
                raise RuntimeError(f"Failed to set API key secret: {stderr}{help_text}")

        if not skip_workflow and branch_name:
            update_progress()
            compare_url = (
                f"https://github.com/{repo_name}/compare/{default_branch}...{branch_name}"
                f"?quick_pull=1&title={quote(PR_TITLE)}&body={quote(PR_BODY)}"
            )
            await open_browser(compare_url)

        log_event(
            "tengu_setup_github_actions_completed",
            {
                "skip_workflow": skip_workflow,
                "has_api_key": bool(api_key_or_oauth_token),
                "auth_type": auth_type,
                "using_default_secret_name": secret_name == "ANTHROPIC_API_KEY",
                "selected_vivian_workflow": "vivian" in selected_workflows,
                "selected_vivian_review_workflow": "vivian-review" in selected_workflows,
                **context,
            },
        )
        save_global_config(
            lambda current: {
                **current,
                "githubActionSetupCount": (current.get("githubActionSetupCount") or 0) + 1,
            }
        )
    except Exception as error:
        if "Failed to" not in str(error):
            log_event(
                "tengu_setup_github_actions_failed",
                {"reason": "unexpected_error", **context},
            )
        logging.exception("setup_github_actions failed")
        raise
