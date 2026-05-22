"""Port of src/utils/suggestions/slackChannelSuggestions.ts - Slack channel completions."""
from __future__ import annotations
from typing import Any, Optional, Dict, List, Set
import re
import asyncio
import logging

logger = logging.getLogger(__name__)

_channel_cache: Optional[List[str]] = None
_known_channels: Set[str] = set()
_cache_lock = asyncio.Lock() if False else None  # created lazily
_subscribers: List[Any] = []


# Observable-style known channels change signal
class _KnownChannelsSignal:
    def __init__(self) -> None:
        self._subscribers: List[Any] = []

    def subscribe(self, fn: Any) -> Any:
        self._subscribers.append(fn)
        return lambda: self._subscribers.remove(fn)

    def emit(self, value: Any) -> None:
        for fn in list(self._subscribers):
            try:
                fn(value)
            except Exception:
                pass


knownChannelsChanged = _KnownChannelsSignal()
subscribeKnownChannels = knownChannelsChanged.subscribe


def _find_slack_client(clients: List[Any]) -> Optional[Any]:
    """Find first client that represents a Slack MCP server."""
    for client in clients:
        name = ''
        if hasattr(client, 'name'):
            name = client.name
        elif isinstance(client, dict):
            name = client.get('name', '')
        if 'slack' in name.lower():
            return client
    _input = clients
    _output = _input if _input is not None else {}
    return _output


findSlackClient = _find_slack_client


def _unwrap_results(text: str) -> List[str]:
    """Parse Slack search_channels result text into channel names.
    
    Expected format: lines like 'Name: #channel-name' or '#channel-name'.
    """
    channels: List[str] = []
    for line in text.splitlines():
        # Try 'Name: #channel' format
        m = re.search(r'Name:\s*#?(\S+)', line)
        if m:
            channels.append('#' + m.group(1).lstrip('#'))
            continue
        # Try bare '#channel'
        m2 = re.match(r'#(\S+)', line.strip())
        if m2:
            channels.append('#' + m2.group(1))
    return channels


unwrapResults = _unwrap_results


async def fetch_channels(clients: List[Any], query: str = '') -> List[str]:
    """Fetch Slack channels via MCP tool call, with cache."""
    global _channel_cache

    if _channel_cache is not None:
        return _channel_cache

    slack_client = _find_slack_client(clients)
    if not slack_client:
        logger.debug("No Slack MCP client found")
        return []

    try:
        # Call the Slack MCP tool
        if hasattr(slack_client, 'call_tool'):
            result = await slack_client.call_tool('slack_search_channels', {'query': query})
        elif isinstance(slack_client, dict) and callable(slack_client.get('callTool')):
            result = await slack_client['callTool']('slack_search_channels', {'query': query})
        else:
            logger.debug("Slack client has no call_tool method")
            return []

        text = ''
        if isinstance(result, str):
            text = result
        elif isinstance(result, dict):
            text = result.get('text', '') or str(result.get('content', ''))
        elif isinstance(result, list):
            text = '\n'.join(str(r) for r in result)

        channels = _unwrap_results(text)
        _channel_cache = channels
        for ch in channels:
            _known_channels.add(ch)
        if channels:
            knownChannelsChanged.emit(set(_known_channels))
        return channels
    except Exception as e:
        logger.debug(f"Slack channel fetch failed: {e}")
        return []


fetchChannels = fetch_channels


async def get_slack_channel_suggestions(
    input_text: str,
    clients: List[Any],
) -> List[Dict[str, Any]]:
    """Return Slack channel completions that start with input_text."""
    channels = await fetch_channels(clients)
    query = input_text.lstrip('#').lower()
    matches = [ch for ch in channels if ch.lstrip('#').lower().startswith(query)]
    return [
        {
            'value': ch,
            'label': ch,
            'known': ch in _known_channels,
        }
        for ch in matches
    ]


getSlackChannelSuggestions = get_slack_channel_suggestions

