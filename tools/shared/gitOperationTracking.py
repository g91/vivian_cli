"""Git operation tracking — mirrors src/tools/shared/gitOperationTracking.ts"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

class GitOperationType(str, Enum):
    COMMIT = "commit"
    PUSH = "push"
    PULL = "pull"
    BRANCH = "branch"
    MERGE = "merge"
    REBASE = "rebase"
    STASH = "stash"
    CHECKOUT = "checkout"

@dataclass
class GitOperation:
    type: GitOperationType
    description: str
    timestamp: float = 0.0
    success: bool = True
    error: Optional[str] = None

@dataclass
class GitOperationTracker:
    operations: List[GitOperation] = field(default_factory=list)
    
    def track(self, op: GitOperation) -> None:
        """Track a git operation."""
        import time
        op.timestamp = time.time()
        self.operations.append(op)
    
    def getRecentOperations(self, count: int = 10) -> List[GitOperation]:
        """Get the most recent git operations."""
        return self.operations[-count:]
    
    def clear(self) -> None:
        """Clear all tracked operations."""
        self.operations.clear()

# Global tracker instance
gitTracker = GitOperationTracker()
