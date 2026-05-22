"""perf-issue command — mirrors src/commands/perf-issue/.

Analyze and report performance issues.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    import sys
    lines = ["Performance Snapshot:", ""]
    lines.append(f"  Python version: {sys.version.split()[0]}")
    try:
        import psutil
        mem = psutil.Process().memory_info()
        lines.append(f"  Memory RSS: {mem.rss / 1024 / 1024:.1f} MB")
        lines.append(f"  CPU percent: {psutil.Process().cpu_percent(interval=0.1):.1f}%")
    except ImportError:
        lines.append("  Install psutil for detailed perf stats")
    try:
        qe = getattr(context, "query_engine", None)
        if qe:
            lines.append(f"  Messages in memory: {len(getattr(qe, 'messages', []))}")
            lines.append(f"  Total tokens: {getattr(qe, 'total_input_tokens', 0) + getattr(qe, 'total_output_tokens', 0):,}")
    except Exception:
        pass
    return TextResult("\n".join(lines))


reportPerfIssue = call
report_perf_issue = call
