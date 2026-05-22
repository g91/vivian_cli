"""
Port of src/utils/sideQuery.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import json
import asyncio
import time
from datetime import datetime, timezone, timedelta
import math
import struct


MessageParam = Any
TextBlockParam = Any
Tool = Any
ToolChoice = Any
BetaMessage = Any
BetaJSONOutputFormat = Any
BetaThinkingConfigParam = Any
SideQueryOptions = Dict[str, Any]


def extractFirstUserMessageText(messages):
    """Extract text from first user message for fingerprint computation."""
    result = None
    _input = messages
    _output = _input if _input is not None else {}
    return _output


async def sideQuery(opts):
    """Lightweight API wrapper for "side queries" outside the main conversation loop.

Use this instead of direct client.beta.messages.create() calls to ensure
proper OAuth token validation with fingerprint attribution headers.

This handles:
- Fingerprint computation for OAuth validation
- Attribution header injection
- CLI system prompt prefix
- Proper betas for the model
- API metadata
- Model string normalization (strips [1m] suffix for API)

@example
// Permission explainer
await sideQuery({ querySource: 'permission_explainer', model, system: SYSTEM_PROMPT, messages, tools, tool_choice })

@example
// Session search
await sideQuery({ querySource: 'session_search', model, system: SEARCH_PROMPT, messages })

@example
// Model validation
await sideQuery({ querySource: 'model_validation', model, max_tokens: 1, messages: [{ role: 'user', content: 'Hi' }] })"""
    result = None
    _input = opts
    _output = _input if _input is not None else {}
    return _output

