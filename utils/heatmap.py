"""
    pass of src/utils/heatmap
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
from datetime import datetime, timedelta
import math

from .statsCache import to_date_string


HeatmapOptions = Dict[str, Any]
Percentiles = Dict[str, Any]


def calculatePercentiles(dailyActivity):
    """Pre-calculates percentiles from activity data for use in intensity calculations"""
    counts = sorted(
        [int(item.get('messageCount', 0)) for item in (dailyActivity or []) if int(item.get('messageCount', 0)) > 0]
    )
    if not counts:
        return None
    return {
        'p25': counts[math.floor(len(counts) * 0.25)],
        'p50': counts[math.floor(len(counts) * 0.5)],
        'p75': counts[math.floor(len(counts) * 0.75)],
    }


def generateHeatmap(dailyActivity, options=None):
    """Generates a GitHub-style activity heatmap for the terminal"""
    options = options or {}
    terminal_width = int(options.get('terminalWidth', 80))
    show_month_labels = bool(options.get('showMonthLabels', True))

    day_label_width = 4
    available_width = terminal_width - day_label_width
    width = min(52, max(10, available_width))

    activity_map = {item.get('date'): item for item in (dailyActivity or []) if item.get('date')}
    percentiles = calculatePercentiles(dailyActivity)

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    current_week_start = today - timedelta(days=(today.weekday() + 1) % 7)
    start_date = current_week_start - timedelta(days=(width - 1) * 7)

    grid = [['' for _ in range(width)] for _ in range(7)]
    month_starts = []
    last_month = -1
    current_date = start_date

    for week in range(width):
        for day in range(7):
            if current_date > today:
                grid[day][week] = ' '
                current_date += timedelta(days=1)
                continue

            date_str = to_date_string(current_date)
            activity = activity_map.get(date_str)

            if day == 0:
                month = current_date.month - 1
                if month != last_month:
                    month_starts.append({'month': month, 'week': week})
                    last_month = month

            intensity = getIntensity((activity or {}).get('messageCount', 0), percentiles)
            grid[day][week] = getHeatmapChar(intensity)
            current_date += timedelta(days=1)

    lines = []
    if show_month_labels:
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        unique_months = [entry['month'] for entry in month_starts]
        label_width = max(1, math.floor(width / max(len(unique_months), 1)))
        month_labels = ''.join(month_names[month].ljust(label_width) for month in unique_months)
        lines.append('    ' + month_labels)

    day_labels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    for day in range(7):
        label = day_labels[day].ljust(3) if day in (1, 3, 5) else '   '
        lines.append(label + ' ' + ''.join(grid[day]))

    lines.append('')
    lines.append('    Less ' + ' '.join(getHeatmapChar(i) for i in range(1, 5)) + ' More')
    return '\n'.join(lines)


def getIntensity(messageCount, percentiles):
    if messageCount == 0 or not percentiles:
        return 0
    if messageCount >= percentiles['p75']:
        return 4
    if messageCount >= percentiles['p50']:
        return 3
    if messageCount >= percentiles['p25']:
        return 2
    return 1


def getHeatmapChar(intensity):
    if intensity == 0:
        return '·'
    if intensity == 1:
        return '░'
    if intensity == 2:
        return '▒'
    if intensity == 3:
        return '▓'
    if intensity == 4:
        return '█'
    return '·'


calculate_percentiles = calculatePercentiles
generate_heatmap = generateHeatmap
get_intensity = getIntensity
get_heatmap_char = getHeatmapChar