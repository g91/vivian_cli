"""Performance monitoring — mirrors src/hooks/usePerformanceMonitor.ts."""
from __future__ import annotations

def usePerformanceMonitor() -> dict:
    """Monitor performance metrics."""
    return {"fps": 60, "latency": 0}

use_performance_monitor = usePerformanceMonitor
