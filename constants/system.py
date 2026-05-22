"""System constants — mirrors src/constants/system.ts."""
from __future__ import annotations

import os
import platform
from typing import Optional

PRODUCT_NAME = "Vivian CLI"
PRODUCT_VERSION = "1.0.0"

DEFAULT_BASE_URL = "https://api.anthropic.com"
DEFAULT_MODEL = "vivian-sonnet-4-20250514"
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TEMPERATURE = 1.0
DEFAULT_TOP_P = 1.0
DEFAULT_MAX_TURNS = 25
MAX_OUTPUT_TOKENS_RECOVERY_LIMIT = 3

ERROR_IDS = {
    "TOOL_USE_SUMMARY_GENERATION_FAILED": 344,
}

FRONTIER_MODEL_NAME = "vivian Sonnet 4"

vivian_4_5_OR_4_6_MODEL_IDS = {
    "opus": "vivian-opus-4-6-20250514",
    "sonnet": "vivian-sonnet-4-6-20250514",
    "haiku": "vivian-haiku-4-5-20250514",
}


def getCwd() -> str:
    return os.getcwd()


async def getIsGit() -> bool:
    """Check if cwd is a git repo."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def getUnameSR() -> str:
    """Get OS version string like 'Linux 6.6.4'."""
    return f"{platform.system()} {platform.release()}"


def getShellInfoLine() -> str:
    shell = os.environ.get("SHELL", "unknown")
    if "zsh" in shell:
        shell_name = "zsh"
    elif "bash" in shell:
        shell_name = "bash"
    else:
        shell_name = shell
    if platform.system() == "Windows":
        return f"Shell: {shell_name} (use Unix shell syntax)"
    return f"Shell: {shell_name}"


def getKnowledgeCutoff(model_id: str) -> Optional[str]:
    """Get knowledge cutoff date for a model."""
    if "vivian-sonnet-4-6" in model_id:
        return "August 2025"
    elif "vivian-opus-4-6" in model_id:
        return "May 2025"
    elif "vivian-opus-4-5" in model_id:
        return "May 2025"
    elif "vivian-haiku-4" in model_id:
        return "February 2025"
    elif "vivian-opus-4" in model_id or "vivian-sonnet-4" in model_id:
        return "January 2025"
    return None


async def computeEnvInfo(model_id: str, additional_working_directories: Optional[list[str]] = None) -> str:
    """Compute environment info for system prompt."""
    is_git = await getIsGit()
    uname_sr = getUnameSR()
    cwd = getCwd()
    shell_line = getShellInfoLine()
    cutoff = getKnowledgeCutoff(model_id)

    additional = ""
    if additional_working_directories:
        additional = f"Additional working directories: {', '.join(additional_working_directories)}\n"

    cutoff_msg = f"\n\nAssistant knowledge cutoff is {cutoff}." if cutoff else ""

    return f"""Here is useful information about the environment you are running in:
<env>
Working directory: {cwd}
Is directory a git repo: {'Yes' if is_git else 'No'}
{additional}Platform: {platform.system()}
{shell_line}
OS Version: {uname_sr}
</env>
You are powered by {FRONTIER_MODEL_NAME}.{cutoff_msg}"""


async def enhanceSystemPromptWithEnvDetails(
    existing_system_prompt: list[str],
    model: str,
    additional_working_directories: Optional[list[str]] = None,
    enabled_tool_names: Optional[set] = None,
) -> list[str]:
    """Enhance system prompt with environment details."""
    notes = """Notes:
- Agent threads always have their cwd reset between bash calls, as a result please only use absolute file paths.
- In your final response, share file paths (always absolute, never relative) that are relevant to the task.
- For clear communication with the user the assistant MUST avoid using emojis.
- Do not use a colon before tool calls."""
    env_info = await computeEnvInfo(model, additional_working_directories)
    return [*existing_system_prompt, notes, env_info]


get_cwd = getCwd
get_is_git = getIsGit
get_uname_sr = getUnameSR
get_shell_info_line = getShellInfoLine
get_knowledge_cutoff = getKnowledgeCutoff
compute_env_info = computeEnvInfo
enhance_system_prompt_with_env_details = enhanceSystemPromptWithEnvDetails
