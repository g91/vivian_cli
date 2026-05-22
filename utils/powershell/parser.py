"""Port of src/utils/powershell/parser.ts."""
from __future__ import annotations

import base64
import os
import re
from typing import Any, Dict, List


PipelineElementType = str
CommandElementType = str
CommandElementChild = Dict[str, Any]
StatementType = str
ParsedCommandElement = Dict[str, Any]
ParsedRedirection = Dict[str, Any]
ParsedStatement = Dict[str, Any]
ParsedVariable = Dict[str, Any]
ParseError = Dict[str, Any]
ParsedPowerShellCommand = Dict[str, Any]
RawCommandElement = Dict[str, Any]
RawRedirection = Dict[str, Any]
RawPipelineElement = Dict[str, Any]
RawStatement = Dict[str, Any]
RawParsedOutput = Dict[str, Any]
SecurityFlags = Dict[str, Any]


PARSE_SCRIPT_BODY = "# Native PowerShell AST parser not embedded in the Python port"
WINDOWS_MAX_COMMAND_LENGTH = 32_760
MAX_COMMAND_LENGTH = 100_000
DEFAULT_PARSE_TIMEOUT_MS = 5_000
COMMON_ALIASES: Dict[str, str] = {
    "%": "foreach-object",
    "?": "where-object",
    "cd": "set-location",
    "chdir": "set-location",
    "sl": "set-location",
    "pushd": "push-location",
    "popd": "pop-location",
    "iex": "invoke-expression",
    "iwr": "invoke-webrequest",
    "irm": "invoke-restmethod",
    "ipmo": "import-module",
    "gci": "get-childitem",
    "gi": "get-item",
    "ni": "new-item",
    "ri": "remove-item",
    "mi": "move-item",
    "si": "set-item",
    "copy": "copy-item",
    "cat": "get-content",
    "gc": "get-content",
    "echo": "write-output",
    "write": "write-output",
    "sleep": "start-sleep",
    "ft": "format-table",
    "fl": "format-list",
    "fw": "format-wide",
    "fc": "format-custom",
    "oh": "out-host",
    "sal": "set-alias",
    "nal": "new-alias",
    "sv": "set-variable",
    "nv": "new-variable",
    "iwmi": "invoke-wmimethod",
}
PS_TOKENIZER_DASH_CHARS = {"-", "–", "—", "―"}
DIRECTORY_CHANGE_CMDLETS = {"set-location", "push-location", "pop-location"}
DIRECTORY_CHANGE_ALIASES = {"cd", "chdir", "sl", "pushd", "popd"}
_VAR_RE = re.compile(r"\$(?:(?P<scope>[A-Za-z_][A-Za-z0-9_]*):)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)")
_REDIR_RE = re.compile(r"^(?P<stream>\d+|\*)?(?P<op>>{1,2}|<)(?P<merge>&\d+)?$")


def getParseTimeoutMs():
    env = os.environ.get("vivian_CODE_PWSH_PARSE_TIMEOUT_MS", "")
    if env.isdigit() and int(env) > 0:
        return int(env)
    return DEFAULT_PARSE_TIMEOUT_MS


def makeInvalidResult(command, message, errorId):
    return {
        "valid": False,
        "errors": [{"message": message, "errorId": errorId}],
        "statements": [],
        "variables": _extract_variables(command or ""),
        "hasStopParsing": False,
        "originalCommand": command or "",
        "typeLiterals": [],
        "hasUsingStatements": False,
        "hasScriptRequirements": False,
    }


def toUtf16LeBase64(text):
    return base64.b64encode(str(text).encode("utf-16le")).decode("ascii")


def buildParseScript(command):
    return f"# parse\n{command}"


def ensureArray(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def mapStatementType(rawType):
    return rawType or "PipelineAst"


def mapElementType(rawType, expressionType=None):
    if rawType:
        return rawType
    return expressionType or "StringConstant"


def classifyCommandName(name):
    lowered = (name or "").lower()
    if not lowered:
        return "unknown"
    if any(sep in lowered for sep in ("/", "\\")) or lowered.endswith((".exe", ".bat", ".cmd", ".ps1")):
        return "application"
    if "-" in lowered or lowered in COMMON_ALIASES:
        return "cmdlet"
    return "unknown"


def stripModulePrefix(name):
    if "\\" in (name or ""):
        return name.split("\\")[-1]
    if "/" in (name or ""):
        return name.split("/")[-1]
    if ":" in (name or "") and not name.startswith("$"):
        return name.split(":")[-1]
    return name


def transformCommandAst(raw):
    return raw


def transformExpressionElement(raw):
    return raw


def transformRedirection(raw):
    return raw


def transformStatement(raw):
    return raw


def transformRawOutput(raw):
    return raw


def _has_unbalanced_quotes(command: str) -> bool:
    single = double = False
    escape = False
    for ch in command:
        if escape:
            escape = False
            continue
        if ch == "`":
            escape = True
            continue
        if ch == "'" and not double:
            single = not single
        elif ch == '"' and not single:
            double = not double
    return single or double


def _split_top_level(command: str, separators: set[str]) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    single = double = False
    brace_depth = 0
    i = 0
    while i < len(command):
        ch = command[i]
        if ch == "`":
            current.append(ch)
            if i + 1 < len(command):
                current.append(command[i + 1])
                i += 2
                continue
        if ch == "'" and not double:
            single = not single
        elif ch == '"' and not single:
            double = not double
        elif not single and not double:
            if ch == "{":
                brace_depth += 1
            elif ch == "}" and brace_depth > 0:
                brace_depth -= 1
            elif brace_depth == 0:
                two = command[i : i + 2]
                if two in separators:
                    part = "".join(current).strip()
                    if part:
                        parts.append(part)
                    current = []
                    i += 2
                    continue
                if ch in separators:
                    part = "".join(current).strip()
                    if part:
                        parts.append(part)
                    current = []
                    i += 1
                    continue
        current.append(ch)
        i += 1
    part = "".join(current).strip()
    if part:
        parts.append(part)
    return parts


def _tokenize(command: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    single = double = False
    brace_depth = 0
    i = 0
    while i < len(command):
        ch = command[i]
        if ch == "`":
            if i + 1 < len(command):
                current.append(command[i + 1])
                i += 2
                continue
        if ch == "'" and not double:
            single = not single
            i += 1
            continue
        if ch == '"' and not single:
            double = not double
            i += 1
            continue
        if not single and not double:
            if ch == "{":
                brace_depth += 1
            elif ch == "}" and brace_depth > 0:
                brace_depth -= 1
            if brace_depth == 0 and ch.isspace():
                if current:
                    tokens.append("".join(current))
                    current = []
                i += 1
                continue
        current.append(ch)
        i += 1
    if current:
        tokens.append("".join(current))
    return tokens


def _extract_variables(command: str) -> list[ParsedVariable]:
    variables: list[ParsedVariable] = []
    for match in _VAR_RE.finditer(command or ""):
        scope = (match.group("scope") or "").lower() or None
        name = match.group("name")
        variables.append({"scope": scope, "name": name, "text": match.group(0)})
    return variables


def _element_type(token: str) -> str:
    if token.startswith("$"):
        return "Variable"
    if token.startswith("{") and token.endswith("}"):
        return "ScriptBlock"
    if isPowerShellParameter(token):
        return "Parameter"
    if "$" in token and token.startswith('"'):
        return "ExpandableString"
    return "StringConstant"


def _extract_redirections(tokens: list[str]) -> tuple[list[str], list[ParsedRedirection]]:
    kept: list[str] = []
    redirections: list[ParsedRedirection] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        match = _REDIR_RE.match(token)
        if match and i + 1 < len(tokens):
            target = tokens[i + 1]
            redirections.append(
                {
                    "type": "FileRedirectionAst",
                    "append": match.group("op") == ">>",
                    "fromStream": match.group("stream") or "1",
                    "locationText": target,
                    "target": target,
                    "isMerging": bool(match.group("merge")),
                }
            )
            i += 2
            continue
        kept.append(token)
        i += 1
    return kept, redirections


def _parse_pipeline_element(segment: str) -> ParsedCommandElement | None:
    tokens = _tokenize(segment)
    if not tokens:
        return None
    tokens, redirections = _extract_redirections(tokens)
    if not tokens:
        return None
    raw_name = tokens[0]
    name = stripModulePrefix(raw_name)
    args = tokens[1:]
    element_types = [_element_type(token) for token in tokens]
    return {
        "name": name,
        "nameType": classifyCommandName(name),
        "elementType": "CommandAst",
        "args": args,
        "text": segment.strip(),
        "elementTypes": element_types,
        "children": None,
        "redirections": redirections,
    }


async def parsePowerShellCommandImpl(command):
    """Parse a PowerShell command with a lightweight tokenizer fallback."""
    if command is None:
        return makeInvalidResult(command, "Command is required", "empty_command")
    if len(command) > MAX_COMMAND_LENGTH:
        return makeInvalidResult(command, "Command exceeds max length", "command_too_long")
    if _has_unbalanced_quotes(command):
        return makeInvalidResult(command, "Unbalanced quotes", "unbalanced_quotes")

    statements: list[ParsedStatement] = []
    for statement_text in _split_top_level(command, {";", "&&", "||"}):
        commands = [
            parsed
            for parsed in (_parse_pipeline_element(piece) for piece in _split_top_level(statement_text, {"|"}))
            if parsed is not None
        ]
        redirections = [redir for cmd in commands for redir in (cmd.get("redirections") or [])]
        statements.append(
            {
                "type": "PipelineAst",
                "text": statement_text,
                "commands": commands,
                "nestedCommands": [],
                "redirections": redirections,
                "securityPatterns": deriveSecurityFlags({"originalCommand": statement_text, "statements": []}),
            }
        )
    return {
        "valid": True,
        "errors": [],
        "statements": statements,
        "variables": _extract_variables(command),
        "hasStopParsing": "--%" in command,
        "originalCommand": command,
        "typeLiterals": re.findall(r"\[[^\]]+\]", command),
        "hasUsingStatements": bool(re.search(r"\busing\s+[A-Za-z]", command, re.IGNORECASE)),
        "hasScriptRequirements": "#requires" in command.lower(),
    }


async def parsePowerShellCommand(command):
    return await parsePowerShellCommandImpl(command)


def getAllCommandNames(parsed):
    names = []
    for statement in parsed.get("statements", []):
        for cmd in statement.get("commands", []):
            names.append(str(cmd.get("name", "")).lower())
        for cmd in statement.get("nestedCommands", []) or []:
            names.append(str(cmd.get("name", "")).lower())
    return names


def getAllCommands(parsed):
    commands = []
    for statement in parsed.get("statements", []):
        commands.extend(statement.get("commands", []))
        commands.extend(statement.get("nestedCommands", []) or [])
    return commands


def getAllRedirections(parsed):
    redirections = []
    for statement in parsed.get("statements", []):
        redirections.extend(statement.get("redirections", []))
        for cmd in statement.get("nestedCommands", []) or []:
            redirections.extend(cmd.get("redirections", []) or [])
    return redirections


def getVariablesByScope(parsed, scope):
    scope_lower = (scope or "").lower()
    return [var for var in parsed.get("variables", []) if (var.get("scope") or "").lower() == scope_lower]


def hasCommandNamed(parsed, name):
    target = (name or "").lower()
    return any(cmd_name == target for cmd_name in getAllCommandNames(parsed))


def hasDirectoryChange(parsed):
    for cmd_name in getAllCommandNames(parsed):
        if cmd_name in DIRECTORY_CHANGE_CMDLETS or cmd_name in DIRECTORY_CHANGE_ALIASES:
            return True
    return False


def isSingleCommand(parsed):
    statements = parsed.get("statements", [])
    if len(statements) != 1:
        return False
    stmt = statements[0]
    return len(stmt.get("commands", [])) == 1 and not (stmt.get("nestedCommands") or [])


def commandHasArg(command, arg):
    target = (arg or "").lower()
    return any(str(value).lower() == target for value in command.get("args", []))


def isPowerShellParameter(arg, elementType=None):
    if elementType == "Parameter":
        return True
    if not isinstance(arg, str) or len(arg) < 2:
        return False
    return arg[0] in PS_TOKENIZER_DASH_CHARS and not arg[1].isdigit()


def commandHasArgAbbreviation(command, fullParam, minPrefix):
    full_lower = (fullParam or "").lower()
    min_prefix_lower = (minPrefix or "").lower()
    for arg in command.get("args", []):
        lowered = str(arg).lower()
        if lowered == full_lower:
            return True
        if lowered.startswith(min_prefix_lower) and full_lower.startswith(lowered):
            return True
    return False


def getPipelineSegments(parsed):
    return [cmd for statement in parsed.get("statements", []) for cmd in statement.get("commands", [])]


def isNullRedirectionTarget(target):
    return str(target).lower() == "$null"


def getFileRedirections(parsed):
    return [redir for redir in getAllRedirections(parsed) if not redir.get("isMerging") and not isNullRedirectionTarget(redir.get("target"))]


def deriveSecurityFlags(parsed):
    command = parsed.get("originalCommand", "") if isinstance(parsed, dict) else str(parsed)
    return {
        "hasMemberInvocations": "." in command,
        "hasSubExpressions": "$(" in command,
        "hasExpandableStrings": '"' in command and "$" in command,
        "hasScriptBlocks": "{" in command and "}" in command,
    }


get_parse_timeout_ms = getParseTimeoutMs
make_invalid_result = makeInvalidResult
to_utf16_le_base64 = toUtf16LeBase64
build_parse_script = buildParseScript
ensure_array = ensureArray
map_statement_type = mapStatementType
map_element_type = mapElementType
classify_command_name = classifyCommandName
strip_module_prefix = stripModulePrefix
parse_power_shell_command_impl = parsePowerShellCommandImpl
parse_power_shell_command = parsePowerShellCommand
get_all_command_names = getAllCommandNames
get_all_commands = getAllCommands
get_variables_by_scope = getVariablesByScope
has_command_named = hasCommandNamed
has_directory_change = hasDirectoryChange
is_single_command = isSingleCommand
command_has_arg = commandHasArg
is_power_shell_parameter = isPowerShellParameter
command_has_arg_abbreviation = commandHasArgAbbreviation
get_pipeline_segments = getPipelineSegments
is_null_redirection_target = isNullRedirectionTarget
get_file_redirections = getFileRedirections
derive_security_flags = deriveSecurityFlags

