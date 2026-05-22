"""Model cost tiers — mirrors src/utils/modelCost.ts"""
from __future__ import annotations

from typing import TypedDict


class ModelCosts(TypedDict):
    input_tokens: float          # per million tokens (USD)
    output_tokens: float
    prompt_cache_write_tokens: float
    prompt_cache_read_tokens: float
    web_search_requests: float


COST_TIER_3_15: ModelCosts = {
    "input_tokens": 3.0,
    "output_tokens": 15.0,
    "prompt_cache_write_tokens": 3.75,
    "prompt_cache_read_tokens": 0.3,
    "web_search_requests": 0.01,
}

COST_TIER_15_75: ModelCosts = {
    "input_tokens": 15.0,
    "output_tokens": 75.0,
    "prompt_cache_write_tokens": 18.75,
    "prompt_cache_read_tokens": 1.5,
    "web_search_requests": 0.01,
}

COST_TIER_5_25: ModelCosts = {
    "input_tokens": 5.0,
    "output_tokens": 25.0,
    "prompt_cache_write_tokens": 6.25,
    "prompt_cache_read_tokens": 0.5,
    "web_search_requests": 0.01,
}

COST_TIER_30_150: ModelCosts = {
    "input_tokens": 30.0,
    "output_tokens": 150.0,
    "prompt_cache_write_tokens": 37.5,
    "prompt_cache_read_tokens": 3.0,
    "web_search_requests": 0.01,
}

COST_HAIKU_35: ModelCosts = {
    "input_tokens": 0.8,
    "output_tokens": 4.0,
    "prompt_cache_write_tokens": 1.0,
    "prompt_cache_read_tokens": 0.08,
    "web_search_requests": 0.01,
}

COST_HAIKU_45: ModelCosts = {
    "input_tokens": 1.0,
    "output_tokens": 5.0,
    "prompt_cache_write_tokens": 1.25,
    "prompt_cache_read_tokens": 0.1,
    "web_search_requests": 0.01,
}

DEFAULT_UNKNOWN_MODEL_COST: ModelCosts = COST_TIER_5_25


def calculate_cost(
    usage: dict,
    costs: ModelCosts = DEFAULT_UNKNOWN_MODEL_COST,
) -> float:
    """Return estimated cost in USD for the given usage dict.

    Usage dict keys: input_tokens, output_tokens,
    cache_creation_input_tokens, cache_read_input_tokens.
    """
    input_tok = usage.get("input_tokens", 0)
    output_tok = usage.get("output_tokens", 0)
    cache_write = usage.get("cache_creation_input_tokens") or 0
    cache_read = usage.get("cache_read_input_tokens") or 0

    return (
        (input_tok * costs["input_tokens"])
        + (output_tok * costs["output_tokens"])
        + (cache_write * costs["prompt_cache_write_tokens"])
        + (cache_read * costs["prompt_cache_read_tokens"])
    ) / 1_000_000
