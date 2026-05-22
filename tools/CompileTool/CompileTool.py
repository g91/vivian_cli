"""
CompileTool — cross-platform source code compiler.

Detects available compilers (GCC, Clang, MSVC, etc.) on Windows, Linux, and macOS
and compiles C, C++, or other supported source files, returning structured results
the AI can use to iterate on errors.
"""
from __future__ import annotations

import asyncio
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TOOL_NAME = "Compile"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["source_file"],
    "properties": {
        "source_file": {
            "type": "string",
            "description": "Path to the source file to compile (e.g. main.c, hello.cpp).",
        },
        "output_file": {
            "type": "string",
            "description": (
                "Path for the compiled output binary. "
                "Defaults to the source filename without extension (plus .exe on Windows)."
            ),
        },
        "language": {
            "type": "string",
            "enum": ["c", "cpp", "auto"],
            "description": "Source language. 'auto' detects from file extension (default).",
        },
        "compiler": {
            "type": "string",
            "description": (
                "Override the compiler to use. "
                "Options: 'gcc', 'g++', 'clang', 'clang++', 'cl' (MSVC), 'auto' (default). "
                "'auto' picks the best available compiler."
            ),
        },
        "flags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Extra compiler flags (e.g. [\"-O2\", \"-Wall\", \"-lm\"]).",
        },
        "working_dir": {
            "type": "string",
            "description": "Directory to run the compiler in. Defaults to the source file's directory.",
        },
        "timeout": {
            "type": "number",
            "description": "Compilation timeout in seconds (default 60).",
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "success":        {"type": "boolean"},
        "compiler_used":  {"type": "string"},
        "output_file":    {"type": "string"},
        "stdout":         {"type": "string"},
        "stderr":         {"type": "string"},
        "exit_code":      {"type": "integer"},
        "command":        {"type": "string"},
        "available_compilers": {"type": "array", "items": {"type": "string"}},
        "error":          {"type": "string"},
    },
}


# ---------------------------------------------------------------------------
# Compiler detection
# ---------------------------------------------------------------------------

# (executable_name, language_support, display_name)
_COMPILER_CANDIDATES: List[Tuple[str, List[str], str]] = [
    ("gcc",      ["c", "cpp"],  "GCC"),
    ("g++",      ["cpp"],       "G++"),
    ("clang",    ["c", "cpp"],  "Clang"),
    ("clang++",  ["cpp"],       "Clang++"),
    ("cc",       ["c"],         "cc"),
    ("c++",      ["cpp"],       "c++"),
]

# MSVC paths to probe on Windows
_MSVC_SEARCH_PATHS: List[str] = [
    # VS 2022 / 2019 default install paths
    r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC",
    r"C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Tools\MSVC",
    r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Tools\MSVC",
    r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Tools\MSVC",
    r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\VC\Tools\MSVC",
    r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\VC\Tools\MSVC",
    r"C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\VC\Tools\MSVC",
]


def _find_msvc_cl() -> Optional[str]:
    """Return the path to MSVC cl.exe if found, else None."""
    # First try PATH
    cl = shutil.which("cl")
    if cl:
        return cl
    if platform.system() != "Windows":
        return None
    # Probe known VS installation paths
    for base in _MSVC_SEARCH_PATHS:
        base_path = Path(base)
        if not base_path.exists():
            continue
        # Each sub-directory is a version number; pick the latest
        try:
            versions = sorted(base_path.iterdir(), reverse=True)
            for ver in versions:
                # Architecture sub-dir: x64/x86
                for arch in ("x64", "x86", "arm64"):
                    cl_path = ver / "bin" / f"Host{arch}" / arch / "cl.exe"
                    if cl_path.exists():
                        return str(cl_path)
        except OSError:
            continue
    return None


def detect_compilers() -> Dict[str, str]:
    """
    Detect all available compilers.
    Returns a dict of {display_name: executable_path}.
    """
    found: Dict[str, str] = {}
    for exe, _langs, display in _COMPILER_CANDIDATES:
        path = shutil.which(exe)
        if path:
            found[display] = path

    cl_path = _find_msvc_cl()
    if cl_path:
        found["MSVC (cl.exe)"] = cl_path

    return found


def _detect_language(source_file: str) -> str:
    """Detect language from file extension."""
    ext = Path(source_file).suffix.lower()
    if ext in {".c"}:
        return "c"
    if ext in {".cpp", ".cxx", ".cc", ".c++"}:
        return "cpp"
    return "c"  # default


def _pick_compiler(language: str, compiler_override: Optional[str]) -> Optional[Tuple[str, str]]:
    """
    Pick the best compiler for the given language.
    Returns (executable, display_name) or None.
    """
    if compiler_override and compiler_override.lower() != "auto":
        path = shutil.which(compiler_override)
        if not path and compiler_override.lower() in ("cl", "msvc"):
            path = _find_msvc_cl()
        if path:
            return (path, compiler_override)
        return None

    # Auto-detect: prefer g++ for C++, gcc for C, then clang, then MSVC
    if language == "cpp":
        preference = ["g++", "clang++", "gcc", "c++", "clang"]
    else:
        preference = ["gcc", "clang", "cc"]

    for exe in preference:
        path = shutil.which(exe)
        if path:
            return (path, exe)

    # Fall back to MSVC
    cl = _find_msvc_cl()
    if cl:
        return (cl, "cl.exe (MSVC)")

    return None


def _build_command(
    compiler_path: str,
    compiler_name: str,
    source_file: str,
    output_file: str,
    language: str,
    extra_flags: List[str],
) -> List[str]:
    """Build the compiler command list."""
    is_msvc = "cl.exe" in compiler_path.lower() or compiler_name.lower() in ("cl", "cl.exe", "msvc")

    if is_msvc:
        # MSVC syntax: cl.exe /Fe:output.exe source.c [flags]
        cmd = [compiler_path, f"/Fe:{output_file}", source_file]
        if language == "cpp":
            cmd.append("/TP")  # Force C++ compilation
        cmd += extra_flags
    else:
        # GCC/Clang syntax: gcc -o output source.c [flags]
        cmd = [compiler_path, "-o", output_file, source_file]
        cmd += extra_flags

    return cmd


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def description() -> str:
    return (
        "Compile C, C++, or other source code using the best available compiler "
        "(GCC, Clang, MSVC, etc.) on the current platform."
    )


async def prompt() -> str:
    compilers = detect_compilers()
    compiler_list = ", ".join(compilers.keys()) if compilers else "none detected"
    return (
        f"Use this tool to compile source code files. "
        f"Available compilers on this system: {compiler_list}. "
        "Provide the source_file path. The tool auto-detects language and compiler. "
        "Returns success status, compiler output, and the output binary path."
    )


def userFacingName() -> str:
    return ""


def getToolUseSummary(input_data: Dict[str, Any]) -> str:
    return input_data.get("source_file", "")


def getActivityDescription(input_data: Dict[str, Any]) -> str:
    src = Path(input_data.get("source_file", "file")).name
    return f"Compiling {src}"


def _resolve_path(file_path: str, context: Any) -> Path:
    p = Path(file_path).expanduser()
    if not p.is_absolute():
        cwd = context.get("cwd", os.getcwd()) if isinstance(context, dict) else os.getcwd()
        p = Path(cwd) / p
    return p.resolve()


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    source_raw = (
        input_data.get("source_file")
        or input_data.get("file")
        or input_data.get("path")
        or input_data.get("source")
        or ""
    )
    if not source_raw:
        return {"success": False, "error": "source_file is required"}

    cwd_ctx = context.get("cwd", os.getcwd()) if isinstance(context, dict) else os.getcwd()
    source_path = _resolve_path(source_raw, context)

    if not source_path.exists():
        return {
            "success": False,
            "error": f"Source file not found: {source_path}",
            "available_compilers": list(detect_compilers().keys()),
        }

    # Language detection
    lang_input = (input_data.get("language") or "auto").lower()
    language = _detect_language(str(source_path)) if lang_input == "auto" else lang_input

    # Compiler selection
    compiler_override = input_data.get("compiler") or "auto"
    compiler_result = _pick_compiler(language, compiler_override)

    available = detect_compilers()
    if not compiler_result:
        return {
            "success": False,
            "error": (
                f"No compiler found for language '{language}'. "
                "Install GCC (mingw-w64 on Windows), Clang, or Visual Studio."
            ),
            "available_compilers": list(available.keys()),
        }

    compiler_path, compiler_display = compiler_result

    # Output file
    is_windows = platform.system() == "Windows"
    output_raw = input_data.get("output_file")
    if output_raw:
        output_path = _resolve_path(output_raw, context)
    else:
        stem = source_path.stem
        suffix = ".exe" if is_windows else ""
        output_path = source_path.parent / f"{stem}{suffix}"

    # Extra flags
    extra_flags: List[str] = input_data.get("flags") or []

    # Working directory
    working_dir_raw = input_data.get("working_dir")
    if working_dir_raw:
        working_dir = str(_resolve_path(working_dir_raw, context))
    else:
        working_dir = str(source_path.parent)

    # Build command
    cmd = _build_command(
        compiler_path,
        compiler_display,
        str(source_path),
        str(output_path),
        language,
        extra_flags,
    )

    timeout_sec = float(input_data.get("timeout") or 60)
    cmd_str = " ".join(cmd)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_sec
            )
        except asyncio.TimeoutError:
            proc.kill()
            return {
                "success": False,
                "compiler_used": compiler_display,
                "command": cmd_str,
                "stdout": "",
                "stderr": f"Compilation timed out after {int(timeout_sec)}s",
                "exit_code": 124,
                "available_compilers": list(available.keys()),
            }

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = proc.returncode or 0
        success = exit_code == 0 and output_path.exists()

        return {
            "success": success,
            "compiler_used": compiler_display,
            "output_file": str(output_path) if success else None,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "command": cmd_str,
            "available_compilers": list(available.keys()),
        }

    except FileNotFoundError:
        return {
            "success": False,
            "error": f"Compiler executable not found: {compiler_path}",
            "available_compilers": list(available.keys()),
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "available_compilers": list(available.keys()),
        }
