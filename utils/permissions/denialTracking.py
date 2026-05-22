"""Port of src/utils/permissions/denialTracking.ts"""
from __future__ import annotations
from typing import TypedDict


class DenialTrackingState(TypedDict):
    consecutiveDenials: int
    totalDenials: int


DENIAL_LIMITS = {
    'maxConsecutive': 3,
    'maxTotal': 20,
}


def createDenialTrackingState() -> DenialTrackingState:
    """Create initial denial tracking state with zero counts."""
    return {'consecutiveDenials': 0, 'totalDenials': 0}


def recordDenial(state: DenialTrackingState) -> DenialTrackingState:
    """Record a denial, incrementing both consecutive and total counters."""
    return {
        'consecutiveDenials': state['consecutiveDenials'] + 1,
        'totalDenials': state['totalDenials'] + 1,
    }


def recordSuccess(state: DenialTrackingState) -> DenialTrackingState:
    """Record a success, resetting the consecutive denial counter."""
    if state['consecutiveDenials'] == 0:
        return state
    return {**state, 'consecutiveDenials': 0}


def shouldFallbackToPrompting(state: DenialTrackingState) -> bool:
    """Return True if denial limits have been exceeded and we should fall back to prompting."""
    return (
        state['consecutiveDenials'] >= DENIAL_LIMITS['maxConsecutive'] or
        state['totalDenials'] >= DENIAL_LIMITS['maxTotal']
    )
