"""REPLTool — mirrors src/tools/REPLTool/REPLTool.tsx"""
from __future__ import annotations

import asyncio
import json
import subprocess
import threading
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from shutil import which
from typing import Any, Dict

from ...bootstrap.state import getSessionId

TOOL_NAME = "REPL"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["language", "code"],
    "properties": {
        "language": {
            "type": "string",
            "enum": ["javascript", "typescript", "python"],
            "description": "The language for the REPL session",
        },
        "code": {"type": "string", "description": "Code to evaluate"},
    },
}


async def description() -> str:
    return "Evaluate code in a REPL session."


async def prompt() -> str:
    return (
        "Use this tool to evaluate code snippets in a REPL environment. "
        "State persists across calls within the same session."
    )


_PYTHON_GLOBALS: dict[str, dict[str, Any]] = {}
_NODE_SESSIONS: dict[str, "_NodeSession"] = {}


class _NodeSession:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._process = subprocess.Popen(
            [
                "node",
                "-e",
                (
                    "const vm=require('node:vm');"
                    "const util=require('node:util');"
                    "const readline=require('node:readline');"
                    "const context=vm.createContext({globalThis:{}});"
                    "context.globalThis=context;"
                    "const rl=readline.createInterface({input:process.stdin,crlfDelay:Infinity});"
                    "rl.on('line', line => {"
                    " let msg;"
                    " try { msg = JSON.parse(line); } catch (err) {"
                    "   process.stdout.write(JSON.stringify({output:'', error:String(err)})+'\\n');"
                    "   return;"
                    " }"
                    " const out=[];"
                    " const consoleShim={"
                    "   log:(...args)=>out.push(args.map(a=>typeof a==='string'?a:util.inspect(a,{depth:4})).join(' ')),"
                    "   error:(...args)=>out.push(args.map(a=>typeof a==='string'?a:util.inspect(a,{depth:4})).join(' '))"
                    " };"
                    " context.console=consoleShim;"
                    " try {"
                    "   const result=vm.runInContext(msg.code, context);"
                    "   if (result !== undefined) out.push(typeof result==='string'?result:util.inspect(result,{depth:4}));"
                    "   process.stdout.write(JSON.stringify({output:out.join('\\n'), error:null})+'\\n');"
                    " } catch (err) {"
                    "   process.stdout.write(JSON.stringify({output:out.join('\\n'), error:String(err && err.stack || err)})+'\\n');"
                    " }"
                    "});"
                ),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def run(self, code: str) -> Dict[str, Any]:
        with self._lock:
            if self._process.poll() is not None or self._process.stdin is None or self._process.stdout is None:
                raise RuntimeError("Node REPL session is not available")
            self._process.stdin.write(json.dumps({"code": code}) + "\n")
            self._process.stdin.flush()
            line = self._process.stdout.readline()
            if not line:
                error = "Node REPL session terminated unexpectedly"
                if self._process.stderr is not None:
                    stderr_tail = self._process.stderr.read().strip()
                    if stderr_tail:
                        error = f"{error}: {stderr_tail}"
                return {"output": "", "error": error}
            return json.loads(line)


def _get_session_key(context: Any) -> str:
    if isinstance(context, dict):
        session_id = context.get("session_id") or context.get("sessionId")
        if isinstance(session_id, str) and session_id:
            return session_id
    return getSessionId()


def _get_python_globals(session_key: str) -> dict[str, Any]:
    if session_key not in _PYTHON_GLOBALS:
        _PYTHON_GLOBALS[session_key] = {"__builtins__": __builtins__}
    return _PYTHON_GLOBALS[session_key]


def _run_python(code: str, session_key: str) -> Dict[str, Any]:
    globals_dict = _get_python_globals(session_key)
    buffer = StringIO()
    try:
        with redirect_stdout(buffer), redirect_stderr(buffer):
            try:
                compiled_eval = compile(code, "<repl>", "eval")
            except SyntaxError:
                compiled_eval = None

            if compiled_eval is not None:
                result = eval(compiled_eval, globals_dict, globals_dict)
                output = buffer.getvalue()
                if result is not None:
                    output += repr(result)
                return {"output": output, "error": None}

            compiled_exec = compile(code, "<repl>", "exec")
            exec(compiled_exec, globals_dict, globals_dict)  # noqa: S102 - intentional REPL execution
        return {"output": buffer.getvalue(), "error": None}
    except Exception as exc:
        import traceback

        return {"output": buffer.getvalue(), "error": "".join(traceback.format_exception(exc))}


def _get_node_session(session_key: str) -> _NodeSession:
    session = _NODE_SESSIONS.get(session_key)
    if session is None:
        session = _NodeSession()
        _NODE_SESSIONS[session_key] = session
    return session


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    lang = input_data.get("language", "python")
    code = input_data.get("code", "")
    session_key = _get_session_key(context)

    if lang == "python":
        return _run_python(code, session_key)

    if lang in {"javascript", "typescript"}:
        if which("node") is None:
            return {"output": "", "error": "Node.js is required for JavaScript and TypeScript REPL support."}
        return await asyncio.to_thread(_get_node_session(session_key).run, code)

    return {"output": "", "error": f"Unsupported REPL language: {lang}"}
