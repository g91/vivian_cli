"""AskUserQuestionTool — mirrors src/tools/AskUserQuestionTool/AskUserQuestionTool.tsx"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from .prompt import ASK_USER_QUESTION_TOOL_NAME, DESCRIPTION, ASK_USER_QUESTION_TOOL_PROMPT

TOOL_NAME = ASK_USER_QUESTION_TOOL_NAME

INPUT_SCHEMA = {
    "type": "object",
    "required": ["question", "options"],
    "properties": {
        "question": {
            "type": "string",
            "description": "The question to ask the user",
        },
        "options": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["label"],
                "properties": {
                    "label": {"type": "string"},
                    "description": {"type": "string"},
                    "preview": {"type": "string"},
                    "recommended": {"type": "boolean"},
                },
            },
            "description": "The options for the user to choose from",
        },
        "multiSelect": {
            "type": "boolean",
            "description": "Allow multiple selections",
            "default": False,
        },
        "selectedOptions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The options selected by the user",
        },
        "customInput": {
            "type": "string",
            "description": "Custom freeform input supplied by the user",
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "selectedOptions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "customInput": {"type": "string"},
    },
}


async def description() -> str:
    return DESCRIPTION


async def prompt() -> str:
    return ASK_USER_QUESTION_TOOL_PROMPT


def userFacingName() -> str:
    return ""


async def checkPermissions(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return {"behavior": "ask", "message": "Answer question?", "updatedInput": input_data}


async def call(input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the AskUserQuestion tool — mirrors the call() export from TS."""
    question = input_data.get("question", "")
    options = input_data.get("options", [])
    multi_select = input_data.get("multiSelect", False)
    selected_options = input_data.get("selectedOptions", []) or []
    custom_input = input_data.get("customInput", "") or ""

    return {
        "question": question,
        "options": options,
        "multiSelect": multi_select,
        "selectedOptions": selected_options,
        "customInput": custom_input,
    }
