"""BashTool package — mirrors src/tools/BashTool/"""
from .toolName import BASH_TOOL_NAME
from .BashTool import (
    TOOL_NAME,
    INPUT_SCHEMA,
    OUTPUT_SCHEMA,
    isSearchOrReadBashCommand,
    detectBlockedSleepPattern,
    call,
    description,
    prompt,
    userFacingName,
    getToolUseSummary,
    getActivityDescription,
)
from .commandSemantics import interpretCommandResult
from .commentLabel import extractBashCommentLabel
from .destructiveCommandWarning import getDestructiveCommandWarning
from .modeValidation import checkPermissionMode, getAutoAllowedCommands
from .bashPermissions import (
    bashToolHasPermission,
    commandHasAnyCd,
    matchWildcardPattern,
    permissionRuleExtractPrefix,
    BINARY_HIJACK_VARS,
    stripSafeWrappers,
    stripAllLeadingEnvVars,
    isNormalizedCdCommand,
    isNormalizedGitCommand,
)
from .bashSecurity import bashCommandIsSafe_DEPRECATED, bashCommandIsSafeAsync_DEPRECATED, parseForSecurity
from .shouldUseSandbox import shouldUseSandbox
from .sedEditParser import parseSedEditCommand, isSedInPlaceEdit, SedEditInfo
from .sedValidation import sedCommandIsAllowedByAllowlist, isLinePrintingCommand

__all__ = [
    "BASH_TOOL_NAME",
    "TOOL_NAME",
    "INPUT_SCHEMA",
    "OUTPUT_SCHEMA",
    "isSearchOrReadBashCommand",
    "detectBlockedSleepPattern",
    "interpretCommandResult",
    "extractBashCommentLabel",
    "getDestructiveCommandWarning",
    "checkPermissionMode",
    "getAutoAllowedCommands",
    "bashToolHasPermission",
    "commandHasAnyCd",
    "matchWildcardPattern",
    "permissionRuleExtractPrefix",
    "BINARY_HIJACK_VARS",
    "stripSafeWrappers",
    "stripAllLeadingEnvVars",
    "isNormalizedCdCommand",
    "isNormalizedGitCommand",
    "bashCommandIsSafe_DEPRECATED",
    "bashCommandIsSafeAsync_DEPRECATED",
    "parseForSecurity",
    "shouldUseSandbox",
    "parseSedEditCommand",
    "isSedInPlaceEdit",
    "SedEditInfo",
    "sedCommandIsAllowedByAllowlist",
    "isLinePrintingCommand",
]
