"""Port of src/utils/powershell/dangerousCmdlets.ts."""
from __future__ import annotations

from ..permissions.dangerousPatterns import CROSS_PLATFORM_CODE_EXEC
from .parser import COMMON_ALIASES


FILEPATH_EXECUTION_CMDLETS = {
    "invoke-command",
    "start-job",
    "start-threadjob",
    "register-scheduledjob",
}

DANGEROUS_SCRIPT_BLOCK_CMDLETS = {
    "invoke-command",
    "invoke-expression",
    "start-job",
    "start-threadjob",
    "register-scheduledjob",
    "register-engineevent",
    "register-objectevent",
    "register-wmievent",
    "new-pssession",
    "enter-pssession",
}

MODULE_LOADING_CMDLETS = {
    "import-module",
    "ipmo",
    "install-module",
    "save-module",
    "update-module",
    "install-script",
    "save-script",
}

_SHELLS_AND_SPAWNERS = {
    "pwsh",
    "powershell",
    "cmd",
    "bash",
    "wsl",
    "sh",
    "start-process",
    "start",
    "add-type",
    "new-object",
}


def aliasesOf(targets):
    return [alias for alias, target in COMMON_ALIASES.items() if target.lower() in targets]


NETWORK_CMDLETS = {
    "invoke-webrequest",
    "invoke-restmethod",
}

ALIAS_HIJACK_CMDLETS = {
    "set-alias",
    "sal",
    "new-alias",
    "nal",
    "set-variable",
    "sv",
    "new-variable",
    "nv",
}

WMI_CIM_CMDLETS = {
    "invoke-wmimethod",
    "iwmi",
    "invoke-cimmethod",
}

ARG_GATED_CMDLETS = {
    "select-object",
    "sort-object",
    "group-object",
    "where-object",
    "measure-object",
    "write-output",
    "write-host",
    "start-sleep",
    "format-table",
    "format-list",
    "format-wide",
    "format-custom",
    "out-string",
    "out-host",
    "ipconfig",
    "hostname",
    "route",
}

_core = {
    *_SHELLS_AND_SPAWNERS,
    *FILEPATH_EXECUTION_CMDLETS,
    *DANGEROUS_SCRIPT_BLOCK_CMDLETS,
    *MODULE_LOADING_CMDLETS,
    *NETWORK_CMDLETS,
    *ALIAS_HIJACK_CMDLETS,
    *WMI_CIM_CMDLETS,
    *ARG_GATED_CMDLETS,
    "foreach-object",
    *[pattern for pattern in CROSS_PLATFORM_CODE_EXEC if " " not in pattern],
}
NEVER_SUGGEST = frozenset({*_core, *aliasesOf(_core)})
