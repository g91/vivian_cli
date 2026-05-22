"""usePagination — mirrors src/commands/plugin/usePagination.ts."""
from __future__ import annotations

def use_pagination(items: list, page: int = 1, per_page: int = 10) -> dict:
    total = len(items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    return {
        "items": items[start:start + per_page],
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }
