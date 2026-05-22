"""Extra usage core — mirrors src/commands/extra-usage/extra-usage-core.ts.

Core logic for computing extra usage billing details.
"""

from __future__ import annotations


def is_billed_as_extra_usage(model: str, fast_mode: bool = False) -> bool:
    """Check if a model is billed as extra usage."""
    extra_models = {"opus", "sonnet", "haiku"}
    model_lower = model.lower()
    return any(m in model_lower for m in extra_models)


def compute_extra_usage_cost(
    input_tokens: int,
    output_tokens: int,
    model: str,
) -> float:
    """Compute extra usage cost for a model."""
    if not is_billed_as_extra_usage(model):
        return 0.0
    # Approximate pricing
    rates = {"opus": (15.0, 75.0), "sonnet": (3.0, 15.0), "haiku": (0.25, 1.25)}
    model_lower = model.lower()
    for key, (in_rate, out_rate) in rates.items():
        if key in model_lower:
            return (input_tokens / 1_000_000) * in_rate + (output_tokens / 1_000_000) * out_rate
    return 0.0
