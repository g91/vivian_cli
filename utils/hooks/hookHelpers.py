"""Port of src/utils/hooks/hookHelpers.ts"""
from __future__ import annotations
from typing import Any, Optional, Dict, Callable
import re
import json


def hook_response_schema() -> Dict[str, Any]:
    """JSON schema for hook responses."""
    return {
        'type': 'object',
        'properties': {
            'ok': {'type': 'boolean', 'description': 'Whether the condition was met'},
            'reason': {'type': 'string', 'description': 'Reason, if the condition was not met'},
        },
        'required': ['ok'],
        'additionalProperties': False,
    }


hookResponseSchema = hook_response_schema


def add_arguments_to_prompt(prompt: str, json_input: str) -> str:
    """Replace $ARGUMENTS placeholder in prompt with json_input, or append if not present.
    Also handles $ARGUMENTS[0], $ARGUMENTS[1], $0, $1 indexed forms.
    """
    try:
        parsed = json.loads(json_input)
    except (json.JSONDecodeError, ValueError):
        parsed = None

    # Handle indexed $ARGUMENTS[N] and $N shorthand
    def replace_indexed(m: re.Match) -> str:
        idx_str = m.group(1) or m.group(2)
        if idx_str is None:
            return json_input
        try:
            idx = int(idx_str)
            if isinstance(parsed, list) and 0 <= idx < len(parsed):
                v = parsed[idx]
                return json.dumps(v) if not isinstance(v, str) else v
        except (ValueError, TypeError):
            pass
        return m.group(0)

    if '$ARGUMENTS' in prompt or re.search(r'\$\d+', prompt):
        result = re.sub(r'\$ARGUMENTS\[(\d+)\]|\$(\d+)', replace_indexed, prompt)
        result = result.replace('$ARGUMENTS', json_input)
        return result

    # Append if no placeholder
    return f"{prompt}\n\n{json_input}"


addArgumentsToPrompt = add_arguments_to_prompt


def create_structured_output_tool() -> Dict[str, Any]:
    """Create a StructuredOutput tool configured for hook responses."""
    return {
        'name': 'StructuredOutput',
        'description': 'Return your verification result.',
        'inputSchema': hook_response_schema(),
        'type': 'structured_output',
    }


createStructuredOutputTool = create_structured_output_tool


def register_structured_output_enforcement(
    set_app_state: Callable,
    session_id: str,
) -> None:
    """Register a function hook that enforces structured output via StructuredOutput tool."""
    from vivian_cli.utils.hooks.sessionHooks import add_function_hook

    def check_structured_output(messages: list, signal: Any = None) -> bool:
        # Check if any message has a successful StructuredOutput tool call
        for msg in messages:
            content = msg.get('message', {}).get('content', []) if isinstance(msg, dict) else []
            if isinstance(content, list):
                for block in content:
                    if (isinstance(block, dict)
                            and block.get('type') == 'tool_use'
                            and block.get('name') == 'StructuredOutput'):
                        return True
        if messages is None:
            return False
        return True

    add_function_hook(
        set_app_state,
        session_id,
        'Stop',
        '',
        check_structured_output,
        'You MUST call the StructuredOutput tool to complete this request.',
        {'timeout': 5000},
    )


registerStructuredOutputEnforcement = register_structured_output_enforcement

