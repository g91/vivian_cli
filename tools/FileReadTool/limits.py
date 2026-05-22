"""FileReadTool limits — mirrors src/tools/FileReadTool/limits.ts"""
MAX_LINE_LENGTH = 2000
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_LINES_PER_READ = 2000
TRUNCATION_MESSAGE = "... [truncated]"

def isFileTooLarge(filePath: str) -> bool:
    """Check if a file exceeds the maximum size limit."""
    import os
    try:
        return os.path.getsize(filePath) > MAX_FILE_SIZE_BYTES
    except (FileNotFoundError, PermissionError):
        return False

def truncateLine(line: str) -> str:
    """Truncate a line that exceeds the maximum line length."""
    if len(line) > MAX_LINE_LENGTH:
        return line[:MAX_LINE_LENGTH] + TRUNCATION_MESSAGE
    return line
