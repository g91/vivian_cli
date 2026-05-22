"""install-github-app command — mirrors src/commands/install-github-app/."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ...constants.github_app import GITHUB_ACTION_SETUP_DOCS_URL
from ...services.analytics.index import log_event
from ...utils.auth import get_anthropic_api_key, get_auth_token_source
from ...utils.browser import open_browser
from ...utils.execFileNoThrow import exec_file_no_throw
from ...utils.git.gitFilesystem import get_cached_remote_url
from ...utils.stringUtils import plural
from .setupGitHubActions import setup_github_actions

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


DEFAULT_SECRET_NAME = "ANTHROPIC_API_KEY"
OAUTH_SECRET_NAME = "vivian_CODE_OAUTH_TOKEN"
DEFAULT_WORKFLOWS = ["vivian", "vivian-review"]
INSTALL_URL = "https://github.com/apps/vivian"


@dataclass
class InstallOptions:
    repo: str | None = None
    api_key: str | None = None
    oauth_token: str | None = None
    secret_name: str | None = None
    workflow_action: str | None = None
    workflows: list[str] | None = None
    use_existing_secret: bool = False
    yes: bool = False
    skip_browser: bool = False


def _result_code(result: dict[str, Any]) -> int:
    return int(result.get("code", -1))


def _result_stdout(result: dict[str, Any]) -> str:
    return str(result.get("stdout", ""))


def _result_stderr(result: dict[str, Any]) -> str:
    return str(result.get("stderr", ""))


def _usage() -> str:
    return (
        "Usage: /install-github-app [--repo owner/repo|https://github.com/owner/repo] "
        "[--api-key KEY|--oauth-token TOKEN] [--secret-name NAME] "
        "[--workflow-action update|skip] [--workflow vivian,vivian-review] "
        "[--use-existing-secret] [--yes] [--skip-browser]"
    )


def _parse_args(args: str) -> InstallOptions:
    tokens = shlex.split(args) if args.strip() else []
    options = InstallOptions()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in {"--repo", "-r"} and index + 1 < len(tokens):
            options.repo = tokens[index + 1]
            index += 2
            continue
        if token == "--api-key" and index + 1 < len(tokens):
            options.api_key = tokens[index + 1]
            index += 2
            continue
        if token == "--oauth-token" and index + 1 < len(tokens):
            options.oauth_token = tokens[index + 1]
            index += 2
            continue
        if token == "--secret-name" and index + 1 < len(tokens):
            options.secret_name = tokens[index + 1]
            index += 2
            continue
        if token == "--workflow-action" and index + 1 < len(tokens):
            options.workflow_action = tokens[index + 1]
            index += 2
            continue
        if token == "--workflow" and index + 1 < len(tokens):
            options.workflows = [
                value.strip()
                for value in tokens[index + 1].split(",")
                if value.strip()
            ]
            index += 2
            continue
        if token == "--use-existing-secret":
            options.use_existing_secret = True
            index += 1
            continue
        if token in {"--yes", "-y", "--force"}:
            options.yes = True
            index += 1
            continue
        if token == "--skip-browser":
            options.skip_browser = True
            index += 1
            continue
        raise ValueError(f"Unknown argument: {token}")
    return options


def _parse_repo_name(value: str | None) -> tuple[str, list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    repo_name = (value or "").strip()
    if not repo_name:
        return "", warnings

    if "github.com" in repo_name:
        match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", repo_name)
        if not match:
            warnings.append(
                {
                    "title": "Invalid GitHub URL format",
                    "message": "The repository URL format appears to be invalid.",
                    "instructions": [
                        "Use format: owner/repo or https://github.com/owner/repo",
                        "Example: anthropics/vivian-cli",
                    ],
                }
            )
        else:
            repo_name = match.group(1).replace(".git", "")

    if repo_name and "/" not in repo_name:
        warnings.append(
            {
                "title": "Repository format warning",
                "message": 'Repository should be in format "owner/repo"',
                "instructions": [
                    "Use format: owner/repo",
                    "Example: anthropics/vivian-cli",
                ],
            }
        )
    return repo_name, warnings


async def _get_current_repo() -> str:
    remote_url = await get_cached_remote_url()
    repo_name, _ = _parse_repo_name(remote_url)
    return repo_name


async def _check_github_cli() -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    warnings: list[dict[str, Any]] = []

    gh_version_result = await exec_file_no_throw("gh", ["--version"])
    if _result_code(gh_version_result) != 0:
        warnings.append(
            {
                "title": "GitHub CLI not found",
                "message": "GitHub CLI (gh) does not appear to be installed or accessible.",
                "instructions": [
                    "Install GitHub CLI from https://cli.github.com/",
                    "macOS: brew install gh",
                    "Windows: winget install --id GitHub.cli",
                    "Linux: See installation instructions at https://github.com/cli/cli#installation",
                ],
            }
        )

    auth_result = await exec_file_no_throw("gh", ["auth", "status", "-a"])
    if _result_code(auth_result) != 0:
        warnings.append(
            {
                "title": "GitHub CLI not authenticated",
                "message": "GitHub CLI does not appear to be authenticated.",
                "instructions": [
                    "Run: gh auth login",
                    "Follow the prompts to authenticate with GitHub",
                    "Or set up authentication using environment variables or other methods",
                ],
            }
        )
    else:
        token_scopes_match = re.search(r"Token scopes:.*$", _result_stdout(auth_result), re.MULTILINE)
        if token_scopes_match:
            scopes = token_scopes_match.group(0)
            missing_scopes: list[str] = []
            if "repo" not in scopes:
                missing_scopes.append("repo")
            if "workflow" not in scopes:
                missing_scopes.append("workflow")
            if missing_scopes:
                return warnings, {
                    "error": f"GitHub CLI is missing required permissions: {', '.join(missing_scopes)}.",
                    "reason": "Missing required scopes",
                    "instructions": [
                        f'Your GitHub CLI authentication is missing the "{" and ".join(missing_scopes)}" {plural(len(missing_scopes), "scope")} needed to manage GitHub Actions and secrets.',
                        "",
                        "To fix this, run:",
                        "  gh auth refresh -h github.com -s repo,workflow",
                        "",
                        "This will add the necessary permissions to manage workflows and secrets.",
                    ],
                }
    return warnings, None


async def _check_repository_permissions(repo_name: str) -> tuple[bool, str | None]:
    try:
        result = await exec_file_no_throw("gh", ["api", f"repos/{repo_name}", "--jq", ".permissions.admin"])
        if _result_code(result) == 0:
            return _result_stdout(result).strip() == "true", None
        stderr = _result_stderr(result)
        if "404" in stderr or "Not Found" in stderr:
            return False, "repository_not_found"
    except Exception:
        pass
    return False, None


async def _check_existing_workflow_file(repo_name: str) -> bool:
    result = await exec_file_no_throw(
        "gh",
        ["api", f"repos/{repo_name}/contents/.github/workflows/vivian.yml", "--jq", ".sha"],
    )
    return _result_code(result) == 0


async def _check_existing_secret(repo_name: str) -> bool:
    result = await exec_file_no_throw(
        "gh",
        ["secret", "list", "--app", "actions", "--repo", repo_name],
    )
    if _result_code(result) != 0:
        return False
    return any(re.match(r"^ANTHROPIC_API_KEY\s+", line) for line in _result_stdout(result).splitlines())


def _format_warnings(warnings: list[dict[str, Any]]) -> str:
    lines = ["Setup warnings:", ""]
    for warning in warnings:
        lines.append(f"- {warning.get('title')}: {warning.get('message')}")
        for instruction in warning.get("instructions", []):
            lines.append(f"  {instruction}")
        lines.append("")
    lines.append("Re-run with --yes to continue anyway.")
    return "\n".join(lines).rstrip()


def _format_error(error: str, reason: str | None = None, instructions: list[str] | None = None) -> str:
    lines = ["GitHub App installation failed", "", error]
    if reason:
        lines.extend(["", f"Reason: {reason}"])
    if instructions:
        lines.append("")
        lines.extend(instructions)
    lines.extend(["", f"Manual setup: {GITHUB_ACTION_SETUP_DOCS_URL}"])
    return "\n".join(lines)


def _resolve_workflows(options: InstallOptions, workflow_exists: bool) -> list[str]:
    workflows = options.workflows or list(DEFAULT_WORKFLOWS)
    valid = [workflow for workflow in workflows if workflow in {"vivian", "vivian-review"}]
    if not valid and not workflow_exists:
        return list(DEFAULT_WORKFLOWS)
    return valid


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult

    try:
        options = _parse_args(args)
    except ValueError as error:
        return TextResult(f"{error}\n{_usage()}")

    if options.workflow_action not in {None, "skip", "update"}:
        return TextResult(_usage())

    log_event("tengu_install_github_app_started", {})

    gh_warnings, gh_error = await _check_github_cli()
    if gh_error:
        return TextResult(
            _format_error(
                gh_error["error"],
                gh_error.get("reason"),
                gh_error.get("instructions"),
            )
        )

    current_repo = await _get_current_repo()
    repo_candidate = options.repo or current_repo
    repo_name, repo_warnings = _parse_repo_name(repo_candidate)
    if not repo_name:
        return TextResult(
            "Repository selection required. Re-run with --repo owner/repo or from a git checkout with a GitHub origin.\n"
            + _usage()
        )

    permission_warnings: list[dict[str, Any]] = []
    has_access, permission_error = await _check_repository_permissions(repo_name)
    if permission_error == "repository_not_found":
        permission_warnings.append(
            {
                "title": "Repository not found",
                "message": f"Repository {repo_name} was not found or you don't have access.",
                "instructions": [
                    f"Check that the repository name is correct: {repo_name}",
                    "Ensure you have access to this repository",
                    'For private repositories, make sure your GitHub token has the "repo" scope',
                    "You can add the repo scope with: gh auth refresh -h github.com -s repo,workflow",
                ],
            }
        )
    elif not has_access:
        permission_warnings.append(
            {
                "title": "Admin permissions required",
                "message": f"You might need admin permissions on {repo_name} to set up GitHub Actions.",
                "instructions": [
                    "Repository admins can install GitHub Apps and set secrets",
                    "Ask a repository admin to run this command if setup fails",
                    "Alternatively, you can use the manual setup instructions",
                ],
            }
        )

    workflow_exists = await _check_existing_workflow_file(repo_name)
    warnings = [*gh_warnings, *repo_warnings, *permission_warnings]
    if warnings and not options.yes:
        return TextResult(_format_warnings(warnings))

    if not options.skip_browser:
        await open_browser(INSTALL_URL)

    if workflow_exists and options.workflow_action is None:
        return TextResult(
            "A vivian workflow file already exists in this repository. "
            "Re-run with --workflow-action update to update it or --workflow-action skip to leave workflow files unchanged."
        )

    skip_workflow = options.workflow_action == "skip"
    selected_workflows = _resolve_workflows(options, workflow_exists)
    if not skip_workflow and not selected_workflows:
        return TextResult("At least one workflow must be selected. Use --workflow vivian,vivian-review")

    explicit_token = options.oauth_token or options.api_key
    existing_token = get_anthropic_api_key()
    auth_type = "oauth_token" if options.oauth_token else "api_key"
    if explicit_token is None and existing_token:
        token_source = get_auth_token_source()
        if str(token_source.get("source") or "").startswith("oauth"):
            auth_type = "oauth_token"

    secret_exists = await _check_existing_secret(repo_name)
    token_to_use = explicit_token or existing_token

    if options.oauth_token:
        secret_name = options.secret_name or OAUTH_SECRET_NAME
    else:
        secret_name = options.secret_name or DEFAULT_SECRET_NAME

    if secret_exists:
        if options.use_existing_secret:
            token_to_use = None
            secret_name = DEFAULT_SECRET_NAME
        elif token_to_use is None:
            return TextResult(
                "ANTHROPIC_API_KEY already exists in repository secrets. Re-run with --use-existing-secret to keep using it, "
                "or provide --api-key/--oauth-token to save a new secret."
            )
    elif token_to_use is None:
        return TextResult(
            "No API key or OAuth token is available. Re-run with --api-key KEY, --oauth-token TOKEN, "
            "or authenticate locally before running /install-github-app."
        )

    progress_steps = 0

    def update_progress() -> None:
        nonlocal progress_steps
        progress_steps += 1

    try:
        await setup_github_actions(
            repo_name,
            token_to_use,
            secret_name,
            update_progress,
            skip_workflow,
            selected_workflows,
            auth_type,
            {
                "useCurrentRepo": repo_name == current_repo,
                "workflowExists": workflow_exists,
                "secretExists": secret_exists,
            },
        )
    except Exception as error:
        error_message = str(error) or "Failed to set up GitHub Actions"
        if "workflow file already exists" in error_message:
            log_event("tengu_install_github_app_error", {"reason": "workflow_file_exists"})
            return TextResult(
                _format_error(
                    "A vivian workflow file already exists in this repository.",
                    "Workflow file conflict",
                    [
                        "The file .github/workflows/vivian.yml already exists",
                        "You can either:",
                        "  1. Delete the existing file and run this command again",
                        f"  2. Update the existing file manually using the template from: {GITHUB_ACTION_SETUP_DOCS_URL}",
                    ],
                )
            )
        log_event("tengu_install_github_app_error", {"reason": "setup_github_actions_failed"})
        return TextResult(_format_error(error_message, "GitHub Actions setup failed", []))

    log_event("tengu_install_github_app_completed", {})
    lines = ["GitHub Actions setup complete!", "", f"Repository: {repo_name}"]
    if not skip_workflow:
        lines.append(f"Workflows: {', '.join(selected_workflows)}")
    if secret_exists and options.use_existing_secret:
        lines.append("Using existing ANTHROPIC_API_KEY secret")
    else:
        lines.append(f"Secret configured: {secret_name}")
    if not options.skip_browser:
        lines.append(f"GitHub App install page opened: {INSTALL_URL}")
    return TextResult("\n".join(lines))


installGitHubApp = call
install_github_app = call
