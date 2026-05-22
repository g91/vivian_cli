"""File index package — mirrors src/native-ts/file-index/index.ts."""
from .index import (
    SCORE_MATCH, BONUS_BOUNDARY, BONUS_CAMEL, BONUS_CONSECUTIVE,
    BONUS_FIRST_CHAR, PENALTY_GAP_START, PENALTY_GAP_EXTENSION,
    MAX_QUERY_LEN, TOP_LEVEL_CACHE_LIMIT, CHUNK_MS,
    SearchResult, FileIndex, FileIndexType,
    yieldToEventLoop,
)

__all__ = [
    "SCORE_MATCH", "BONUS_BOUNDARY", "BONUS_CAMEL", "BONUS_CONSECUTIVE",
    "BONUS_FIRST_CHAR", "PENALTY_GAP_START", "PENALTY_GAP_EXTENSION",
    "MAX_QUERY_LEN", "TOP_LEVEL_CACHE_LIMIT", "CHUNK_MS",
    "SearchResult", "FileIndex", "FileIndexType",
    "yieldToEventLoop",
]
