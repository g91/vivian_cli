"""Memory directory package — mirrors src/memdir/."""
from .memory_types import (
    MEMORY_TYPES, MemoryType, parse_memory_type,
    TYPES_SECTION_COMBINED, MEMORY_FRONTMATTER_EXAMPLE,
    WHEN_TO_ACCESS_SECTION, WHAT_NOT_TO_SAVE_SECTION, TRUSTING_RECALL_SECTION,
)
from .memory_age import memory_age_days, memory_age, memory_freshness_text, memory_freshness_note
from .memory_scan import MemoryHeader, scan_memory_files, format_memory_manifest
from .find_relevant_memories import RelevantMemory, find_relevant_memories
from .memdir import (
    ENTRYPOINT_NAME, MAX_ENTRYPOINT_LINES, MAX_ENTRYPOINT_BYTES,
    EntrypointTruncation, truncate_entrypoint_content, ensure_memory_dir_exists,
    DIR_EXISTS_GUIDANCE, DIRS_EXIST_GUIDANCE,
)
from .paths import (
    is_auto_memory_enabled, is_extract_mode_active,
    get_memory_base_dir, get_auto_mem_path, get_memory_dir,
)
from .team_mem_paths import get_team_memory_dir, is_team_memory_enabled
from .team_mem_prompts import get_team_memory_system_prompt_section

__all__ = [
    "MEMORY_TYPES", "MemoryType", "parse_memory_type",
    "TYPES_SECTION_COMBINED", "MEMORY_FRONTMATTER_EXAMPLE",
    "WHEN_TO_ACCESS_SECTION", "WHAT_NOT_TO_SAVE_SECTION", "TRUSTING_RECALL_SECTION",
    "memory_age_days", "memory_age", "memory_freshness_text", "memory_freshness_note",
    "MemoryHeader", "scan_memory_files", "format_memory_manifest",
    "RelevantMemory", "find_relevant_memories",
    "ENTRYPOINT_NAME", "MAX_ENTRYPOINT_LINES", "MAX_ENTRYPOINT_BYTES",
    "EntrypointTruncation", "truncate_entrypoint_content", "ensure_memory_dir_exists",
    "DIR_EXISTS_GUIDANCE", "DIRS_EXIST_GUIDANCE",
    "is_auto_memory_enabled", "is_extract_mode_active",
    "get_memory_base_dir", "get_auto_mem_path", "get_memory_dir",
    "get_team_memory_dir", "is_team_memory_enabled",
    "get_team_memory_system_prompt_section",
]
