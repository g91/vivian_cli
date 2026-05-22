"""
RunScriptTool — run scripts (Python, JS, Ruby, shell, executables) and return
structured output the AI can use to detect errors and iterate until the script works.

Supports: .py, .js, .ts, .rb, .sh, .bash, .ps1, .bat, .cmd, .lua, .r, .go, .exe, and more.
"""
from __future__ import annotations

import asyncio
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TOOL_NAME = "RunScript"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["file_path"],
    "properties": {
        "file_path": {
            "type": "string",
            "description": "Path to the script or executable to run.",
        },
        "args": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Command-line arguments to pass to the script.",
        },
        "stdin": {
            "type": "string",
            "description": "Optional standard input to feed to the script.",
        },
        "working_dir": {
            "type": "string",
            "description": "Working directory to run the script in. Defaults to the script's directory.",
        },
        "timeout": {
            "type": "number",
            "description": "Timeout in seconds (default 30). Use a higher value for long-running scripts.",
        },
        "interpreter": {
            "type": "string",
            "description": (
                "Override the interpreter. E.g. 'python', 'python3', 'node', 'ruby'. "
                "Defaults to auto-detection from file extension."
            ),
        },
        "env": {
            "type": "object",
            "description": "Extra environment variables to set (merged with current env).",
            "additionalProperties": {"type": "string"},
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "success":           {"type": "boolean"},
        "exit_code":         {"type": "integer"},
        "stdout":            {"type": "string"},
        "stderr":            {"type": "string"},
        "interpreter_used":  {"type": "string"},
        "file_path":         {"type": "string"},
        "timed_out":         {"type": "boolean"},
        "error":             {"type": "string"},
        "error_summary":     {"type": "string"},
    },
}

# ---------------------------------------------------------------------------
# Interpreter detection
# ---------------------------------------------------------------------------

# extension → list of interpreter candidates (tried in order)
_INTERPRETERS: Dict[str, List[str]] = {
    ".py":    ["python", "python3", "python3.12", "python3.11", "python3.10", "python3.9"],
    ".js":    ["node", "nodejs"],
    ".mjs":   ["node", "nodejs"],
    ".cjs":   ["node", "nodejs"],
    ".ts":    ["ts-node", "npx ts-node", "deno"],
    ".rb":    ["ruby"],
    ".lua":   ["lua", "lua5.4", "lua5.3"],
    ".r":     ["Rscript"],
    ".R":     ["Rscript"],
    ".pl":    ["perl"],
    ".php":   ["php"],
    ".sh":    ["bash", "sh"],
    ".bash":  ["bash"],
    ".zsh":   ["zsh"],
    ".ps1":   ["pwsh", "powershell"],
    ".bat":   [],   # run directly via cmd /c
    ".cmd":   [],   # run directly via cmd /c
    ".go":    ["go run"],
    ".java":  [],   # needs special handling (javac + java)
}

_IS_WINDOWS = platform.system() == "Windows"


def detect_interpreter(file_path: str, override: Optional[str] = None) -> Optional[Tuple[List[str], str]]:
    """
    Return ([interpreter_args...], display_name) for running file_path.
    Returns None if no interpreter found.
    """
    if override:
        # User-specified interpreter — may be a path or just a name
        interp = shutil.which(override) or override
        return ([interp], override)

    ext = Path(file_path).suffix.lower()

    # Batch files — run via cmd /c on Windows
    if ext in (".bat", ".cmd") and _IS_WINDOWS:
        return (["cmd", "/c", file_path], "cmd.exe")

    # PowerShell
    if ext == ".ps1":
        for cand in ["pwsh", "powershell"]:
            path = shutil.which(cand)
            if path:
                return ([path, "-NonInteractive", "-File"], cand)
        return None

    # Go files — use `go run`
    if ext == ".go":
        go = shutil.which("go")
        if go:
            return ([go, "run"], "go run")
        return None

    # Java files — compile then run
    if ext == ".java":
        javac = shutil.which("javac")
        java = shutil.which("java")
        if javac and java:
            return (["__java__"], "java")
        return None

    # Generic candidates
    candidates = _INTERPRETERS.get(ext, [])
    for cand in candidates:
        # Some candidates are multi-word (e.g. "npx ts-node")
        parts = cand.split()
        exe = shutil.which(parts[0])
        if exe:
            return ([exe] + parts[1:], cand)

    # Fallback: if the file itself is executable (Unix) or .exe (Windows)
    p = Path(file_path)
    if _IS_WINDOWS and p.suffix.lower() == ".exe":
        return ([file_path], "native executable")
    if not _IS_WINDOWS and os.access(file_path, os.X_OK):
        return ([file_path], "native executable")

    return None


def _extract_error_summary(stdout: str, stderr: str, exit_code: int, interpreter: str) -> str:
    """Extract a brief human-readable error summary from script output."""
    if exit_code == 0:
        return ""

    lines = (stderr or stdout or "").splitlines()
    # Python: look for Traceback
    if "python" in interpreter.lower():
        tb_lines = []
        in_tb = False
        for line in lines:
            if line.startswith("Traceback"):
                in_tb = True
            if in_tb:
                tb_lines.append(line)
                if len(tb_lines) >= 15:
                    break
        if tb_lines:
            return "\n".join(tb_lines)

    # Generic: return last 10 non-empty lines of stderr
    non_empty = [l for l in lines if l.strip()]
    return "\n".join(non_empty[-10:]) if non_empty else f"Exit code {exit_code}"


def _resolve_path(file_path: str, context: Any) -> Path:
    p = Path(file_path).expanduser()
    if not p.is_absolute():
        cwd = context.get("cwd", os.getcwd()) if isinstance(context, dict) else os.getcwd()
        p = Path(cwd) / p
    return p.resolve()


# ---------------------------------------------------------------------------
# Java special handling (compile + run)
# ---------------------------------------------------------------------------

async def _run_java(source_path: Path, args: List[str], working_dir: str,
                   stdin_data: Optional[bytes], timeout_sec: float) -> Dict[str, Any]:
    """Compile and run a .java file."""
    javac = shutil.which("javac")
    java = shutil.which("java")
    if not javac or not java:
        return {"success": False, "error": "javac and/or java not found in PATH"}

    # Compile
    compile_proc = await asyncio.create_subprocess_exec(
        javac, str(source_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=working_dir,
    )
    try:
        c_out, c_err = await asyncio.wait_for(compile_proc.communicate(), timeout=30)
    except asyncio.TimeoutError:
        compile_proc.kill()
        return {"success": False, "error": "javac timed out", "exit_code": 124}

    if compile_proc.returncode != 0:
        return {
            "success": False,
            "exit_code": compile_proc.returncode,
            "stdout": c_out.decode("utf-8", errors="replace"),
            "stderr": c_err.decode("utf-8", errors="replace"),
            "interpreter_used": "javac",
            "error_summary": c_err.decode("utf-8", errors="replace")[:500],
        }

    # Run the compiled class
    class_name = source_path.stem
    run_proc = await asyncio.create_subprocess_exec(
        java, class_name, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE if stdin_data else None,
        cwd=working_dir,
    )
    try:
        r_out, r_err = await asyncio.wait_for(
            run_proc.communicate(input=stdin_data), timeout=timeout_sec
        )
        return {
            "success": run_proc.returncode == 0,
            "exit_code": run_proc.returncode,
            "stdout": r_out.decode("utf-8", errors="replace"),
            "stderr": r_err.decode("utf-8", errors="replace"),
            "interpreter_used": "java",
        }
    except asyncio.TimeoutError:
        run_proc.kill()
        return {"success": False, "exit_code": 124, "timed_out": True,
                "error": f"Script timed out after {int(timeout_sec)}s"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def description() -> str:
    return (
        "Run a script or executable (Python, JavaScript, Ruby, shell, PowerShell, etc.) "
        "and return its output and exit status. Use this to test code and catch errors."
    )


async def prompt() -> str:
    py = shutil.which("python") or shutil.which("python3") or "not found"
    node = shutil.which("node") or "not found"
    return (
        "Use this tool to execute scripts and check their output. "
        f"Python: {py}. Node.js: {node}. "
        "The tool auto-detects the interpreter from the file extension. "
        "Returns stdout, stderr, exit_code, and an error_summary if the script failed. "
        "Use in a loop: run → read errors → fix file → run again until success=true."
    )


def userFacingName() -> str:
    return ""


def getToolUseSummary(input_data: Dict[str, Any]) -> str:
    return input_data.get("file_path", "")


def getActivityDescription(input_data: Dict[str, Any]) -> str:
    name = Path(input_data.get("file_path", "script")).name
    return f"Running {name}"


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    file_raw = (
        input_data.get("file_path")
        or input_data.get("path")
        or input_data.get("script")
        or input_data.get("file")
        or ""
    )
    if not file_raw:
        return {"success": False, "error": "file_path is required"}

    file_path = _resolve_path(file_raw, context)
    if not file_path.exists():
        return {"success": False, "error": f"File not found: {file_path}", "file_path": str(file_path)}

    args: List[str] = [str(a) for a in (input_data.get("args") or [])]
    stdin_str: Optional[str] = input_data.get("stdin")
    stdin_data = stdin_str.encode("utf-8") if stdin_str else None
    timeout_sec = float(input_data.get("timeout") or 30)
    interpreter_override = input_data.get("interpreter")
    extra_env: Dict[str, str] = input_data.get("env") or {}

    # Working directory
    working_dir_raw = input_data.get("working_dir")
    if working_dir_raw:
        working_dir = str(_resolve_path(working_dir_raw, context))
    else:
        working_dir = str(file_path.parent)

    # Detect interpreter
    interp_result = detect_interpreter(str(file_path), interpreter_override)
    if interp_result is None:
        return {
            "success": False,
            "error": (
                f"No interpreter found for '{file_path.suffix}' files. "
                "Install the required runtime or specify 'interpreter' explicitly."
            ),
            "file_path": str(file_path),
        }

    interp_args, interp_display = interp_result

    # Java special case
    if interp_args == ["__java__"]:
        result = await _run_java(file_path, args, working_dir, stdin_data, timeout_sec)
        result["file_path"] = str(file_path)
        return result

    # cmd /c .bat handling
    if interp_args[0] == "cmd" and len(interp_args) >= 2 and interp_args[1] == "/c":
        cmd = ["cmd", "/c", str(file_path)] + args
    else:
        # Normal: [interpreter, script_path, ...args]
        cmd = interp_args + [str(file_path)] + args

    # Merge environment
    env = dict(os.environ)
    env.update(extra_env)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if stdin_data else None,
            cwd=working_dir,
            env=env,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=stdin_data), timeout=timeout_sec
            )
        except asyncio.TimeoutError:
            proc.kill()
            return {
                "success": False,
                "timed_out": True,
                "exit_code": 124,
                "stdout": "",
                "stderr": "",
                "interpreter_used": interp_display,
                "file_path": str(file_path),
                "error": f"Script timed out after {int(timeout_sec)}s",
            }

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = proc.returncode if proc.returncode is not None else 0
        success = exit_code == 0
        error_summary = _extract_error_summary(stdout, stderr, exit_code, interp_display)

        result: Dict[str, Any] = {
            "success": success,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "interpreter_used": interp_display,
            "file_path": str(file_path),
        }
        if error_summary:
            result["error_summary"] = error_summary
        return result

    except FileNotFoundError as exc:
        return {
            "success": False,
            "error": f"Interpreter not found: {exc}",
            "file_path": str(file_path),
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "file_path": str(file_path),
        }
