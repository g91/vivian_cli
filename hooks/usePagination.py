"""Pagination — mirrors src/hooks/usePagination.ts."""
from __future__ import annotations
from typing import Any

def usePagination(items: list[Any], pageSize: int = 10) -> dict[str, Any]:
    """Manage pagination."""
    current_page = 0
    
    def next_page() -> list[Any]:
        nonlocal current_page
        current_page += 1
        start = current_page * pageSize
        return items[start:start + pageSize]
    
    def prev_page() -> list[Any]:
        nonlocal current_page
        current_page = max(0, current_page - 1)
        start = current_page * pageSize
        return items[start:start + pageSize]
    
    def goToPage(page: int) -> list[Any]:
        nonlocal current_page
        current_page = page
        start = current_page * pageSize
        return items[start:start + pageSize]
    
    total_pages = (len(items) + pageSize - 1) // pageSize
    
    return {
        "currentPage": current_page,
        "totalPages": total_pages,
        "nextPage": next_page,
        "prevPage": prev_page,
        "goToPage": goToPage,
    }

use_pagination = usePagination
