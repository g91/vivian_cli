"""PowerShell common parameters — mirrors src/tools/PowerShellTool/commonParameters.ts"""
COMMON_PARAMETERS = {
    "-WhatIf",
    "-Confirm",
    "-Verbose",
    "-Debug",
    "-ErrorAction",
    "-WarningAction",
    "-InformationAction",
    "-ErrorVariable",
    "-WarningVariable",
    "-InformationVariable",
    "-OutVariable",
    "-OutBuffer",
    "-PipelineVariable",
}

def isCommonParameter(param: str) -> bool:
    """Check if a parameter is a PowerShell common parameter."""
    return param in COMMON_PARAMETERS
