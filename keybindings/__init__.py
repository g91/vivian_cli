"""Keybindings package — mirrors src/keybindings/."""

from .parser import (
    parseKeystroke,
    parseChord,
    keystrokeToString,
    chordToString,
    keystrokeToDisplayString,
    chordToDisplayString,
    parseBindings,
)
from .match import getKeyName, matchesBinding, matchesKeystroke
from .defaultBindings import DEFAULT_BINDINGS
from .loadUserBindings import (
    disposeKeybindingWatcher,
    getCachedKeybindingWarnings,
    getKeybindingsPath,
    initializeKeybindingWatcher,
    isKeybindingCustomizationEnabled,
    loadKeybindings,
    loadKeybindingsSync,
    loadKeybindingsSyncWithWarnings,
    resetKeybindingLoaderForTesting,
    subscribeToKeybindingChanges,
)
from .reservedShortcuts import (
    NON_REBINDABLE,
    TERMINAL_RESERVED,
    MACOS_RESERVED,
    getReservedShortcuts,
    normalizeKeyForComparison,
)
from .resolver import (
    buildKeystroke,
    getBindingDisplayText,
    keystrokesEqual,
    resolveKey,
    resolveKeyWithChordState,
)
from .schema import (
    KEYBINDING_CONTEXTS,
    KEYBINDING_CONTEXT_DESCRIPTIONS,
    KEYBINDING_ACTIONS,
)
from .shortcutFormat import getShortcutDisplay
from .template import filterReservedShortcuts, generateKeybindingsTemplate
from .types import (
    ChordResolveResult,
    KeybindingBlock,
    KeybindingContextName,
    ParsedBinding,
    ParsedKeystroke,
)
from .KeybindingContext import (
    HandlerRegistration,
    KeybindingContextValue,
    KeybindingProvider,
    useKeybindingContext,
    useOptionalKeybindingContext,
    useRegisterKeybindingContext,
)
from .KeybindingProviderSetup import (
    CHORD_TIMEOUT_MS,
    ChordInterceptor,
    KeybindingSetup,
    disposeKeybindingSetup,
    useKeybindingWarnings,
)
from .useKeybinding import Options, useKeybinding, useKeybindings
from .useShortcutDisplay import useShortcutDisplay
from .validate import (
    checkDuplicateKeysInJson,
    checkDuplicates,
    checkReservedShortcuts,
    formatWarning,
    formatWarnings,
    validateBindings,
    validateUserConfig,
)

__all__ = [
    "CHORD_TO_DISPLAY_STRING",
    "CHORD_TIMEOUT_MS",
    "ChordInterceptor",
    "ChordResolveResult",
    "DEFAULT_BINDINGS",
    "HandlerRegistration",
    "KEYBINDING_ACTIONS",
    "KEYBINDING_CONTEXTS",
    "KEYBINDING_CONTEXT_DESCRIPTIONS",
    "KeybindingBlock",
    "KeybindingContextName",
    "KeybindingContextValue",
    "KeybindingProvider",
    "KeybindingSetup",
    "MACOS_RESERVED",
    "NON_REBINDABLE",
    "Options",
    "ParsedBinding",
    "ParsedKeystroke",
    "TERMINAL_RESERVED",
    "buildKeystroke",
    "checkDuplicateKeysInJson",
    "checkDuplicates",
    "checkReservedShortcuts",
    "chordToDisplayString",
    "chordToString",
    "filterReservedShortcuts",
    "formatWarning",
    "formatWarnings",
    "generateKeybindingsTemplate",
    "getBindingDisplayText",
    "getCachedKeybindingWarnings",
    "getKeyName",
    "getKeybindingsPath",
    "getReservedShortcuts",
    "getShortcutDisplay",
    "initializeKeybindingWatcher",
    "isKeybindingCustomizationEnabled",
    "keystrokeToDisplayString",
    "keystrokeToString",
    "keystrokesEqual",
    "loadKeybindings",
    "loadKeybindingsSync",
    "loadKeybindingsSyncWithWarnings",
    "matchesBinding",
    "matchesKeystroke",
    "normalizeKeyForComparison",
    "parseBindings",
    "parseChord",
    "parseKeystroke",
    "resetKeybindingLoaderForTesting",
    "resolveKey",
    "resolveKeyWithChordState",
    "subscribeToKeybindingChanges",
    "disposeKeybindingSetup",
    "useKeybinding",
    "useKeybindingContext",
    "useKeybindingWarnings",
    "useKeybindings",
    "useOptionalKeybindingContext",
    "useRegisterKeybindingContext",
    "useShortcutDisplay",
    "validateBindings",
    "validateUserConfig",
    "disposeKeybindingWatcher",
]

CHORD_TO_DISPLAY_STRING = chordToDisplayString