"""LSPTool — mirrors src/tools/LSPTool/LSPTool.tsx"""
from __future__ import annotations
import inspect
import json
from pathlib import Path
from typing import Any, Dict

TOOL_NAME = "LSP"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["action", "file_path"],
    "properties": {
        "action": {
            "type": "string",
            "enum": ["hover", "definition", "references", "completion", "diagnostics"],
        },
        "file_path": {"type": "string"},
        "line": {"type": "integer"},
        "character": {"type": "integer"},
    },
}


async def description() -> str:
    return "Query language server protocol features for a file."


async def prompt() -> str:
    return "Use this tool to get LSP features like hover, go-to-definition, and diagnostics."


def _context_value(context: Any, key: str, default: Any = None) -> Any:
    if isinstance(context, dict):
        if key in context:
            return context.get(key, default)
        options = context.get("options")
        if isinstance(options, dict) and key in options:
            return options.get(key, default)
    return getattr(context, key, default)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _file_uri(file_path: str) -> str:
    return Path(file_path).resolve().as_uri()


def _position(input_data: Dict[str, Any]) -> dict[str, int]:
    line = max(int(input_data.get("line", 1)) - 1, 0)
    character = max(int(input_data.get("character", 1)) - 1, 0)
    return {"line": line, "character": character}


async def _manager_request(manager: Any, file_path: str, method: str, params: Dict[str, Any]) -> Any:
    for attr in ("sendRequest", "send_request", "request"):
        fn = getattr(manager, attr, None)
        if callable(fn):
            try:
                return await _maybe_await(fn(file_path, method, params))
            except TypeError:
                return await _maybe_await(fn(method, params))
    raise RuntimeError("LSP manager does not support requests")


async def _ensure_open(manager: Any, file_path: str) -> None:
    is_open = False
    checker = getattr(manager, "isFileOpen", None) or getattr(manager, "is_file_open", None)
    if callable(checker):
        is_open = bool(await _maybe_await(checker(file_path)))
    if is_open:
        return
    opener = getattr(manager, "openFile", None) or getattr(manager, "open_file", None)
    if callable(opener):
        content = Path(file_path).read_text(encoding="utf-8")
        await _maybe_await(opener(file_path, content))


def _get_lsp_manager(context: Any) -> Any:
    return _context_value(context, "lspManager")


def _get_ide_client(context: Any) -> Any:
    mcp_clients = _context_value(context, "mcpClients", []) or []
    for client in mcp_clients:
        name = client.get("name") if isinstance(client, dict) else getattr(client, "name", None)
        ctype = client.get("type") if isinstance(client, dict) else getattr(client, "type", None)
        if name == "ide" and ctype == "connected":
            return client.get("client") if isinstance(client, dict) else getattr(client, "client", client)
    return None


async def _call_ide_rpc(client: Any, method: str, params: Dict[str, Any]) -> Any:
    for attr in ("call_ide_rpc", "callIdeRpc", "call_rpc", "callRpc"):
        fn = getattr(client, attr, None)
        if callable(fn):
            return await _maybe_await(fn(method, params))
    request = getattr(client, "request", None)
    if callable(request):
        try:
            return await _maybe_await(request(method, params))
        except TypeError:
            return await _maybe_await(request({"method": method, "params": params}))
    raise RuntimeError("IDE client does not support RPC requests")


def _format_result(action: str, result: Any) -> Any:
    if action == "hover" and isinstance(result, dict):
        contents = result.get("contents")
        if isinstance(contents, dict):
            return contents.get("value") or contents.get("text") or json.dumps(contents)
        if isinstance(contents, list):
            return "\n\n".join(item.get("value", "") if isinstance(item, dict) else str(item) for item in contents)
        return contents if contents is not None else result
    return result


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    action = str(input_data.get("action", "")).strip()
    file_path = str(input_data.get("file_path", "")).strip()
    if not file_path:
        return {"error": "file_path is required"}

    absolute_path = str(Path(file_path).expanduser().resolve())
    if not Path(absolute_path).exists():
        return {"error": f"File does not exist: {file_path}"}

    manager = _get_lsp_manager(context)
    ide_client = _get_ide_client(context)
    position = _position(input_data)
    file_uri = _file_uri(absolute_path)

    if action == "diagnostics":
        if ide_client is None:
            return {"error": "LSP diagnostics are not available in this context"}
        try:
            result = await _call_ide_rpc(ide_client, "getDiagnostics", {"uri": file_uri})
        except Exception as exc:
            return {"error": str(exc)}
        return {"result": result}

    if manager is None:
        return {"error": "LSP manager is not available in this context"}

    method_map = {
        "hover": "textDocument/hover",
        "definition": "textDocument/definition",
        "references": "textDocument/references",
        "completion": "textDocument/completion",
    }
    method = method_map.get(action)
    if method is None:
        return {"error": f"Unsupported LSP action: {action}"}

    params: Dict[str, Any] = {
        "textDocument": {"uri": file_uri},
        "position": position,
    }
    if action == "references":
        params["context"] = {"includeDeclaration": True}

    try:
        await _ensure_open(manager, absolute_path)
        result = await _manager_request(manager, absolute_path, method, params)
    except Exception as exc:
        return {"error": str(exc)}

    return {"result": _format_result(action, result)}
