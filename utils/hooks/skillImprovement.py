"""Port of src/utils/skillImprovement.ts - Skill improvement via post-sampling hooks."""
from __future__ import annotations
from typing import Any, Optional, Dict, List
import os
import json
import logging

logger = logging.getLogger(__name__)

SkillUpdate = Dict[str, Any]

_USER_TURN_THRESHOLD = 5  # trigger every 5 user turns
_user_turn_count: int = 0
_last_skill_path: Optional[str] = None


def _format_recent_messages(messages: List[Any], max_count: int = 20) -> str:
    """Format the last max_count messages for LLM input."""
    recent = messages[-max_count:] if len(messages) > max_count else messages
    lines = []
    for msg in recent:
        role = 'unknown'
        content = ''
        if isinstance(msg, dict):
            m = msg.get('message', msg)
            role = m.get('role', 'unknown')
            content = m.get('content', '')
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get('type') == 'text':
                            parts.append(block.get('text', ''))
                        elif block.get('type') == 'tool_use':
                            parts.append(f"[tool: {block.get('name', '')}]")
                    else:
                        parts.append(str(block))
                content = ' '.join(parts)
        lines.append(f"{role}: {content[:500]}")
    return '\n'.join(lines)


formatRecentMessages = _format_recent_messages


def _find_project_skill() -> Optional[str]:
    """Find the project SKILL.md in the current directory hierarchy."""
    cwd = os.getcwd()
    dirs_to_check = [cwd]
    current = cwd
    for _ in range(5):  # walk up at most 5 levels
        parent = os.path.dirname(current)
        if parent == current:
            break
        dirs_to_check.append(parent)
        current = parent

    for d in dirs_to_check:
        skill_path = os.path.join(d, '.vivian', 'SKILL.md')
        if os.path.isfile(skill_path):
            return skill_path

    return None


findProjectSkill = _find_project_skill


def create_skill_improvement_hook() -> Dict[str, Any]:
    """Create a post-sampling hook config that checks for skill improvements."""
    global _user_turn_count

    async def hook_fn(messages: List[Any]) -> None:
        global _user_turn_count

        # Count user turns
        if messages and isinstance(messages[-1], dict):
            m = messages[-1].get('message', messages[-1])
            if m.get('role') == 'user':
                _user_turn_count += 1

        if _user_turn_count < _USER_TURN_THRESHOLD:
            return

        _user_turn_count = 0  # reset
        skill_path = _find_project_skill()
        if not skill_path:
            return

        try:
            skill_content = open(skill_path).read()
            recent_summary = _format_recent_messages(messages)
            prompt = (
                f"You are analyzing a conversation to find improvements for a skill document.\n\n"
                f"SKILL.md:\n{skill_content}\n\n"
                f"Recent messages:\n{recent_summary}\n\n"
                f"If you see patterns or improvements to capture, return JSON: "
                f'[{{"section": "...", "update": "..."}}]. Otherwise return []'
            )

            from vivian_cli.services.api.vivian import query_model_without_streaming
            resp = await query_model_without_streaming(
                messages=[{'type': 'user', 'message': {'role': 'user', 'content': prompt}}],
                system_prompt=[{'type': 'text', 'text': 'You analyze conversations for skill improvements.'}],
                model='vivian-haiku-4-5',
                tools=[],
            )
            content = resp.get('content', '')
            if isinstance(content, list):
                content = ' '.join(b.get('text', '') for b in content if isinstance(b, dict))
            content = content.strip()
            if not content or content == '[]':
                return

            updates = json.loads(content)
            if updates:
                skill_name = os.path.basename(os.path.dirname(skill_path))
                await apply_skill_improvement(skill_name, updates)
        except Exception as e:
            logger.debug(f"Skill improvement hook failed: {e}")

    return {'fn': hook_fn, 'description': 'Skill improvement analyzer'}


createSkillImprovementHook = create_skill_improvement_hook


def init_skill_improvement() -> None:
    """Initialize skill improvement if the feature is enabled."""
    try:
        from vivian_cli.utils.hooks.postSamplingHooks import register_post_sampling_hook
        hook = create_skill_improvement_hook()
        register_post_sampling_hook(hook)
        logger.debug("Skill improvement tracking initialized")
    except Exception as e:
        logger.debug(f"Skill improvement init failed: {e}")


initSkillImprovement = init_skill_improvement


async def apply_skill_improvement(
    skill_name: str,
    updates: List[SkillUpdate],
) -> None:
    """Apply skill improvements by rewriting the SKILL.md file."""
    skill_path = _find_project_skill()
    if not skill_path:
        logger.debug(f"Cannot apply skill improvements: no SKILL.md found for '{skill_name}'")
        return

    try:
        with open(skill_path, 'r') as f:
            content = f.read()

        update_lines = ['', '<!-- Auto-improved by skill improvement hook -->']
        for upd in updates:
            section = upd.get('section', 'General')
            text = upd.get('update', '')
            if text:
                update_lines.append(f"\n## {section}\n\n{text}")

        if update_lines:
            content += '\n'.join(update_lines) + '\n'
            with open(skill_path, 'w') as f:
                f.write(content)
            logger.debug(f"Applied {len(updates)} skill improvement(s) to {skill_path}")
    except Exception as e:
        logger.debug(f"Failed to apply skill improvements to {skill_path}: {e}")


applySkillImprovement = apply_skill_improvement

