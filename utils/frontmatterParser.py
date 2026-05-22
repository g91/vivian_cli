"""Frontmatter parser — mirrors src/utils/frontmatterParser.ts"""
from __future__ import annotations


def parse_frontmatter(content: str, file_path: str | None = None) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.

    Returns (frontmatter_dict, remaining_content).
    """
    del file_path
    if not content.startswith("---"):
        return {}, content
    lines = content.split("\n")
    end_idx = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}, content
    try:
        import yaml
        fm = yaml.safe_load("\n".join(lines[1:end_idx]))
        rest = "\n".join(lines[end_idx + 1:])
        return fm or {}, rest
    except Exception:
        return {}, content


def parseFrontmatter(content: str, file_path: str | None = None) -> tuple[dict, str]:
    return parse_frontmatter(content, file_path)
