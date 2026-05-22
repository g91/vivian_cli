"""Port of src/utils/hooks/execHttpHook.ts - Execute HTTP hooks."""
from __future__ import annotations
import os
import re
from typing import Any, Optional, Dict

DEFAULT_HTTP_HOOK_TIMEOUT_MS = 10 * 60 * 1000  # 10 minutes


def _get_http_hook_policy() -> Dict[str, Any]:
    """Read HTTP hook allowlist restrictions from settings."""
    try:
        from vivian_cli.utils.settings.settings import get_initial_settings
        settings = get_initial_settings()
        return {
            'allowedUrls': getattr(settings, 'allowedHttpHookUrls', None),
            'allowedEnvVars': getattr(settings, 'httpHookAllowedEnvVars', None),
        }
    except ImportError:
        return {'allowedUrls': None, 'allowedEnvVars': None}


def url_matches_pattern(url: str, pattern: str) -> bool:
    """Match URL against a pattern with * as wildcard."""
    escaped = re.escape(pattern)
    regex_str = escaped.replace(r'\*', '.*')
    return bool(re.match(f'^{regex_str}$', url))


def sanitize_header_value(value: str) -> str:
    """Strip CR, LF, NUL bytes to prevent HTTP header injection."""
    return re.sub(r'[\r\n\x00]', '', value)


def interpolate_env_vars(value: str, allowed_env_vars: set) -> str:
    """Interpolate $VAR and ${VAR} patterns using only allowlisted env vars."""
    def replacer(m: re.Match) -> str:
        var_name = m.group(1) or m.group(2)
        if var_name not in allowed_env_vars:
            return ''
        return os.environ.get(var_name, '')
    interpolated = re.sub(r'\$\{([A-Z_][A-Z0-9_]*)\}|\$([A-Z_][A-Z0-9_]*)', replacer, value)
    return sanitize_header_value(interpolated)


async def exec_http_hook(
    hook: Dict[str, Any],
    hook_event: str,
    json_input: str,
    signal: Optional[Any] = None,
) -> Dict[str, Any]:
    """Execute an HTTP hook by POSTing json_input to hook['url'].
    
    Returns dict with keys: ok, statusCode, body, error, aborted.
    """
    import asyncio
    try:
        import requests
    except ImportError:
        return {'ok': False, 'body': '', 'error': 'requests library not available'}

    url = hook.get('url', '')
    if not url:
        return {'ok': False, 'body': '', 'error': 'Hook URL is empty'}

    # Enforce URL allowlist
    policy = _get_http_hook_policy()
    allowed_urls = policy.get('allowedUrls')
    if allowed_urls is not None:
        matched = any(url_matches_pattern(url, p) for p in allowed_urls)
        if not matched:
            msg = f"HTTP hook blocked: {url} does not match any pattern in allowedHttpHookUrls"
            return {'ok': False, 'body': '', 'error': msg}

    timeout_ms = hook.get('timeout', DEFAULT_HTTP_HOOK_TIMEOUT_MS / 1000)
    timeout_s = timeout_ms if isinstance(timeout_ms, (int, float)) and timeout_ms < 10000 else timeout_ms / 1000

    # Build headers with env var interpolation
    headers: Dict[str, str] = {'Content-Type': 'application/json'}
    if hook.get('headers'):
        hook_vars = hook.get('allowedEnvVars', [])
        policy_vars = policy.get('allowedEnvVars')
        if policy_vars is not None:
            effective_vars = [v for v in hook_vars if v in policy_vars]
        else:
            effective_vars = hook_vars
        allowed_set = set(effective_vars)
        for name, value in hook['headers'].items():
            headers[name] = interpolate_env_vars(value, allowed_set)

    # SSRF guard: resolve hostname and block private ranges (skip if proxy is set)
    proxy_url = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
    if not proxy_url:
        try:
            from urllib.parse import urlparse
            from vivian_cli.utils.hooks.ssrfGuard import ssrf_guarded_lookup
            parsed = urlparse(url)
            hostname = parsed.hostname
            if hostname:
                ssrf_guarded_lookup(hostname)  # raises ValueError if blocked
        except ImportError:
            pass
        except ValueError as e:
            return {'ok': False, 'body': '', 'error': str(e)}

    try:
        proxies = {'http': proxy_url, 'https': proxy_url} if proxy_url else None
        resp = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: requests.post(
                url,
                data=json_input,
                headers=headers,
                timeout=timeout_s,
                proxies=proxies,
            )
        )
        return {
            'ok': resp.status_code < 400,
            'statusCode': resp.status_code,
            'body': resp.text,
        }
    except Exception as e:
        return {'ok': False, 'body': '', 'error': str(e)}


execHttpHook = exec_http_hook

