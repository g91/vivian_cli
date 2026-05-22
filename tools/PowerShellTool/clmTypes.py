"""PowerShell CLM types — mirrors src/tools/PowerShellTool/clmTypes.ts"""
from enum import Enum

class CLMLanguageMode(str, Enum):
    FULL_LANGUAGE = "FullLanguage"
    CONSTRAINED_LANGUAGE = "ConstrainedLanguage"
    RESTRICTED_LANGUAGE = "RestrictedLanguage"
    NO_LANGUAGE = "NoLanguage"

def isConstrainedMode(mode: str) -> bool:
    """Check if a language mode is constrained."""
    return mode in (CLMLanguageMode.CONSTRAINED_LANGUAGE, CLMLanguageMode.RESTRICTED_LANGUAGE, CLMLanguageMode.NO_LANGUAGE)
