"""Built-in agent definitions package."""
from .vivianCodeGuideAgent import DEFINITION as vivian_CODE_GUIDE_AGENT
from .exploreAgent import DEFINITION as EXPLORE_AGENT
from .generalPurposeAgent import DEFINITION as GENERAL_PURPOSE_AGENT
from .planAgent import DEFINITION as PLAN_AGENT
from .statuslineSetup import DEFINITION as STATUSLINE_SETUP_AGENT
from .verificationAgent import DEFINITION as VERIFICATION_AGENT

ALL_BUILT_IN_AGENTS = [
    EXPLORE_AGENT,
    PLAN_AGENT,
    VERIFICATION_AGENT,
    GENERAL_PURPOSE_AGENT,
    vivian_CODE_GUIDE_AGENT,
    STATUSLINE_SETUP_AGENT,
]

__all__ = [
    "ALL_BUILT_IN_AGENTS",
    "vivian_CODE_GUIDE_AGENT",
    "EXPLORE_AGENT",
    "GENERAL_PURPOSE_AGENT",
    "PLAN_AGENT",
    "STATUSLINE_SETUP_AGENT",
    "VERIFICATION_AGENT",
]
