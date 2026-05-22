"""Shared chat-mode catalog for the Qt and web GUIs."""
from __future__ import annotations

from typing import Any

_MODE_CATALOG: list[dict[str, Any]] = [
    {
        "id": "default",
        "label": "Default",
        "description": "Balanced coding assistant behavior.",
        "employee_only": False,
        "system_prompt": "Stay in balanced coding mode: be pragmatic, code-first, and use tools when they materially improve correctness.",
    },
    {
        "id": "research",
        "label": "Research",
        "description": "Bias toward investigation, synthesis, citations to local evidence, and option comparison before implementation.",
        "employee_only": False,
        "system_prompt": "You are in research mode. Prioritize gathering evidence, comparing options, surfacing constraints, and explicitly separating facts from assumptions before committing to an implementation.",
    },
    {
        "id": "architect",
        "label": "Architect",
        "description": "Focus on system design, interfaces, tradeoffs, and long-term maintainability.",
        "employee_only": False,
        "system_prompt": "You are in architect mode. Focus on interfaces, structure, tradeoffs, migration strategy, and maintainability. Prefer plans and design guidance before code changes unless the user explicitly asks for implementation.",
    },
    {
        "id": "reviewer",
        "label": "Reviewer",
        "description": "Act like a strict code reviewer focused on bugs, regressions, and missing tests.",
        "employee_only": False,
        "system_prompt": "You are in reviewer mode. Prioritize finding correctness bugs, regression risk, missing tests, and weak assumptions. Be skeptical and evidence-driven.",
    },
    {
        "id": "bughunter",
        "label": "Bughunter",
        "description": "Drive toward reproduction, root cause isolation, and high-confidence fixes.",
        "employee_only": False,
        "system_prompt": "You are in bughunter mode. Focus on reproducing failures, isolating root causes, forming falsifiable hypotheses, and validating fixes immediately after each substantive edit.",
    },
    {
        "id": "ultraplan",
        "label": "Ultraplan",
        "description": "Planning-first mode for large or risky work.",
        "employee_only": False,
        "system_prompt": "You are in ultraplan mode. Produce a concrete implementation plan with phases, dependencies, risk points, and validation strategy before making broad changes. Avoid starting wide edits until the plan is coherent.",
    },
    {
        "id": "speed",
        "label": "Speed",
        "description": "Prefer concise, direct execution with minimal ceremony.",
        "employee_only": False,
        "system_prompt": "You are in speed mode. Optimize for fast execution, concise communication, and the smallest safe changes that solve the task.",
    },
    {
        "id": "cognito",
        "label": "Cognito",
        "description": "Deep-analysis mode for internal or advanced investigative workflows.",
        "employee_only": True,
        "system_prompt": "You are in cognito mode. Apply deep analytical rigor, look for hidden dependencies and second-order effects, and reason carefully about system-wide consequences before acting.",
    },
]


def all_chat_modes() -> list[dict[str, Any]]:
    return [dict(item) for item in _MODE_CATALOG]


def available_chat_modes(*, is_employee: bool = False, expose_internal_modes: bool = False) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in _MODE_CATALOG
        if not item.get("employee_only") or is_employee or expose_internal_modes
    ]


def get_chat_mode(mode_id: str | None, *, is_employee: bool = False, expose_internal_modes: bool = False) -> dict[str, Any]:
    allowed = {item["id"]: item for item in available_chat_modes(is_employee=is_employee, expose_internal_modes=expose_internal_modes)}
    if mode_id in allowed:
        return dict(allowed[mode_id])
    return dict(allowed.get("default") or _MODE_CATALOG[0])


def build_mode_prompt_addendum(mode_id: str | None, *, is_employee: bool = False, expose_internal_modes: bool = False) -> str:
    mode = get_chat_mode(mode_id, is_employee=is_employee, expose_internal_modes=expose_internal_modes)
    return f"GUI chat mode: {mode['label']}\n{mode['system_prompt']}"


def compose_mode_prompt(user_prompt: str, mode_id: str | None, *, is_employee: bool = False, expose_internal_modes: bool = False) -> str:
    addendum = build_mode_prompt_addendum(
        mode_id,
        is_employee=is_employee,
        expose_internal_modes=expose_internal_modes,
    ).strip()
    if not addendum:
        return user_prompt
    return f"[Chat mode instructions]\n{addendum}\n\n[User request]\n{user_prompt}"
