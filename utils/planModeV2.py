"""
Port of src/utils/planModeV2.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import struct


PewterLedgerVariant = Optional[str]


def getPlanModeV2AgentCount():
    # Environment variable override takes precedence
    if os.environ.get("vivian_CODE_PLAN_V2_AGENT_COUNT", ""):
        count = parseInt(os.environ.get("vivian_CODE_PLAN_V2_AGENT_COUNT", ""), 10)
        if not isNaN(count) and count > 0 and count <= 10:
            return count
    subscriptionType = getSubscriptionType()
    rateLimitTier = getRateLimitTier()
    if (
    subscriptionType == 'max' and
    rateLimitTier == 'default_vivian_max_20x'
    ):
        return 3
    if subscriptionType == 'enterprise' or subscriptionType == 'team':
        return 3
    return 1


def getPlanModeV2ExploreAgentCount():
    if os.environ.get("vivian_CODE_PLAN_V2_EXPLORE_AGENT_COUNT", ""):
        count = parseInt(
        os.environ.get("vivian_CODE_PLAN_V2_EXPLORE_AGENT_COUNT", ""),
        10,
        )
        if not isNaN(count) and count > 0 and count <= 10:
            return count
    return 3


def isPlanModeInterviewPhaseEnabled():
    """Check if plan mode interview phase is enabled.

Config: ant=always_on, external=tengu_plan_mode_interview_phase gate, envVar=true"""
    result = None
    _enabled = True
    return _enabled


def getPewterLedgerVariant():
    """tengu_pewter_ledger — plan file structure prompt experiment.

Controls the Phase 4 "Final Plan" bullets in the 5-phase plan mode
workflow (messages.ts getPlanPhase4Section). 5-phase is 99% of plan
traffic; interview-phase (ants) is untouched as a reference population.

Arms: null (control), 'trim', 'cut', 'cap' — progressively stricter
guidance on plan file size.

Baseline (control, 14d ending 2026-03-02, N=26.3M):
p50 4,906 chars | p90 11,617 | mean 6,207 | 82% Opus 4.6
Reject rate monotonic with size: 20% at <2K → 50% at 20K+

Primary: session-level Avg Cost (fact__201omjcij85f) — Opus output is
5× input price so cost is an output-weighted proxy. planLengthChars
on tengu_plan_exit is the mechanism but NOT the goal — the cap arm
could shrink the plan file while increasing total output via
write→count→edit cycles.
Guardrail: feedback-bad rate, requests/session (too-thin plans →
more implementation iterations), tool error rate"""
    result = None
    _result: dict = {}
    # Implement getPewterLedgerVariant
    return _result

