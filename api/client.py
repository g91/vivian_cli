"""Core API client for Vivian AI — wraps all REST endpoints."""

from __future__ import annotations

import json
import time
import logging
from typing import Any, Optional, AsyncGenerator, Union

from ..utils.debug_log import dlog as _dlog
from dataclasses import dataclass

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    httpx = None  # type: ignore
    HAS_HTTPX = False

from ..constants import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    REQUEST_TIMEOUT,
)
from ..types import (
    Message,
    ChatCompletionResponse,
    StreamChunk,
    Usage,
    ChatCompletionChoice,
)

logger = logging.getLogger(__name__)


@dataclass
class VivianAuth:
    """Authentication container for Vivian API.

    auth_style controls how the key is transmitted:
        "bearer"    — Authorization: Bearer <key>   (default, OpenAI-compat)
        "x-api-key" — x-api-key: <key>              (Anthropic native)
        "none"      — no auth header                (local Ollama)

    extra_headers are merged into every request (e.g. openrouter referer).
    """
    api_key: Optional[str] = None
    admin_jwt: Optional[str] = None
    session_cookie: Optional[str] = None
    auth_style: str = "bearer"
    extra_headers: dict = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.extra_headers is None:
            self.extra_headers = {}

    @property
    def bearer_token(self) -> Optional[str]:
        return self.api_key or self.admin_jwt

    def auth_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        token = self.bearer_token
        if self.auth_style == "bearer" and token:
            headers["Authorization"] = f"Bearer {token}"
        elif self.auth_style == "x-api-key" and token:
            headers["x-api-key"] = token
        # "none" — no auth header
        if self.session_cookie:
            headers["Cookie"] = self.session_cookie
        headers.update(self.extra_headers)
        return headers


class VivianClient:
    """Full Vivian AI API client.

    Usage:
        client = VivianClient(api_key="viv-xxx")
        # OpenAI-compatible
        response = await client.chat_completions(messages=[...])
        # Admin
        servers = await client.admin.list_servers()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        admin_jwt: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = REQUEST_TIMEOUT,
        default_model: str = DEFAULT_MODEL,
        auth_style: str = "bearer",
        extra_headers: Optional[dict] = None,
    ):
        if not HAS_HTTPX:
            raise ImportError(
                "httpx is required for VivianClient. Install with: pip install httpx"
            )
        self.auth = VivianAuth(
            api_key=api_key,
            admin_jwt=admin_jwt,
            auth_style=auth_style,
            extra_headers=extra_headers or {},
        )
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.default_model = default_model
        self._client: Optional[httpx.AsyncClient] = None

        # Sub-clients
        self.admin = AdminAPI(self)
        self.users = UsersAPI(self)
        self.memory = MemoryAPI(self)
        self.emotion = EmotionAPI(self)
        self.config = ConfigAPI(self)
        self.stats = StatsAPI(self)
        self.news = NewsAPI(self)
        self.logs = LogsAPI(self)
        self.servers = ServersAPI(self)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                # connect/write timeout short; read timeout long for streaming
                timeout=httpx.Timeout(connect=15.0, read=self.timeout, write=15.0, pool=5.0),
                headers=self.auth.auth_headers(),
                # Disable keep-alive to avoid stale pooled connections after
                # long streaming responses.
                limits=httpx.Limits(max_keepalive_connections=0, max_connections=10),
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None,
        stream: bool = False,
    ) -> httpx.Response:
        client = await self._get_client()
        response = await client.request(
            method=method,
            url=path,
            json=json_data,
            params=params,
        )
        response.raise_for_status()
        return response

    # ── Health ──────────────────────────────────────────────

    async def health(self) -> dict:
        """GET /health — no auth required."""
        r = await self._request("GET", "/health")
        return r.json()

    # ── OpenAI-Compatible Endpoints ─────────────────────────

    async def list_models(self) -> dict:
        """GET /v1/models"""
        r = await self._request("GET", "/v1/models")
        return r.json()

    async def list_tools(self) -> list[dict]:
        """GET /v1/tools — returns server-side built-in tools."""
        r = await self._request("GET", "/v1/tools")
        return r.json()

    async def chat_completions(
        self,
        messages: list[Union[Message, dict[str, Any]]],
        model: Optional[str] = None,
        stream: bool = False,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        top_p: float = DEFAULT_TOP_P,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: str = "auto",
        username: Optional[str] = None,
    ) -> Union[ChatCompletionResponse, AsyncGenerator[StreamChunk, None]]:
        """POST /v1/chat/completions — OpenAI-compatible.

        Returns ChatCompletionResponse for non-streaming, or an async generator
        of StreamChunk for streaming.
        """
        serialized_messages = []
        for m in messages:
            if isinstance(m, Message):
                d = {"role": m.role}
                # When an assistant message has tool_calls, omit content (set to null).
                # Ollama and many OpenAI-compatible servers reject a message that has
                # both a non-null content string and tool_calls simultaneously.
                has_tool_calls = m.tool_calls is not None
                if m.content is not None and not has_tool_calls:
                    d["content"] = m.content
                elif has_tool_calls:
                    d["content"] = None  # explicit null keeps the JSON structure valid
                if has_tool_calls:
                    d["tool_calls"] = m.tool_calls
                if m.tool_call_id is not None:
                    d["tool_call_id"] = m.tool_call_id
                if m.name is not None:
                    d["name"] = m.name
                serialized_messages.append(d)
            else:
                serialized_messages.append(m)

        body: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": serialized_messages,
            "stream": stream,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }
        if tools is not None:
            body["tools"] = tools
            body["tool_choice"] = tool_choice
        if username:
            body["user"] = username

        if stream:
            body["stream_options"] = {"include_usage": True}
            return self._stream_chat(body)
        else:
            r = await self._request("POST", "/v1/chat/completions", json_data=body)
            data = r.json()
            return ChatCompletionResponse(
                id=data.get("id", ""),
                object=data.get("object", "chat.completion"),
                created=data.get("created", 0),
                model=data.get("model", ""),
                choices=[
                    ChatCompletionChoice(
                        index=c.get("index", 0),
                        message=Message(
                            role=c.get("message", {}).get("role", "assistant"),
                            content=c.get("message", {}).get("content"),
                            tool_calls=c.get("message", {}).get("tool_calls"),
                        ),
                        finish_reason=c.get("finish_reason"),
                    )
                    for c in data.get("choices", [])
                ],
                usage=Usage(
                    prompt_tokens=data.get("usage", {}).get("prompt_tokens", 0),
                    completion_tokens=data.get("usage", {}).get("completion_tokens", 0),
                    total_tokens=data.get("usage", {}).get("total_tokens", 0),
                ) if data.get("usage") else None,
            )

    async def _stream_chat(
        self, body: dict[str, Any]
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream SSE chat completions."""
        # Log the message roles being sent (not full content to avoid spam)
        msg_summary = [(m.get("role") if isinstance(m, dict) else getattr(m, "role", "?"))
                       for m in body.get("messages", [])]
        _dlog("api: stream_chat msgs=%r model=%r tools=%d",
              msg_summary, body.get("model"), len(body.get("tools") or []))

        client = await self._get_client()
        _chunks_received = 0
        _content_chunks = 0
        async with client.stream(
            "POST", "/v1/chat/completions", json=body
        ) as response:
            if response.status_code != 200:
                body_text = await response.aread()
                _dlog("api: HTTP %d error: %r", response.status_code, body_text[:300])
                response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        _dlog("api: [DONE] after %d chunks (%d with content)",
                              _chunks_received, _content_chunks)
                        break
                    try:
                        data = json.loads(data_str)
                        _chunks_received += 1
                        choices = data.get("choices", [])
                        if not choices and not data.get("usage"):
                            _dlog("api: chunk with no choices and no usage: %r",
                                  data_str[:200])
                        if choices:
                            _content_chunks += 1
                        # Log errors embedded in stream
                        if data.get("error"):
                            _dlog("api: stream error payload: %r", data["error"])
                        chunk = StreamChunk(
                            id=data.get("id", ""),
                            object=data.get("object", "chat.completion.chunk"),
                            created=data.get("created", 0),
                            model=data.get("model", ""),
                            choices=choices,
                            usage=data.get("usage"),
                        )
                        yield chunk
                    except json.JSONDecodeError as e:
                        _dlog("api: json decode error on line %r: %s", line[:200], e)
                        continue
                else:
                    _dlog("api: non-data line: %r", line[:200])

    async def completions(
        self,
        prompt: str,
        model: Optional[str] = None,
        username: Optional[str] = None,
    ) -> dict:
        """POST /v1/completions — legacy text completions."""
        body: dict[str, Any] = {
            "model": model or self.default_model,
            "prompt": prompt,
        }
        if username:
            body["user"] = username
        r = await self._request("POST", "/v1/completions", json_data=body)
        return r.json()


class AdminAPI:
    """Admin API endpoints — requires admin JWT."""

    def __init__(self, client: VivianClient):
        self._client = client

    async def login(self, username: str, password: str) -> str:
        """POST /api/admin/login — returns JWT token."""
        r = await self._client._request(
            "POST", "/api/admin/login",
            json_data={"username": username, "password": password},
        )
        data = r.json()
        token = data["token"]
        self._client.auth.admin_jwt = token
        return token


class UsersAPI:
    """User self-service endpoints — requires API key."""

    def __init__(self, client: VivianClient):
        self._client = client

    async def register(
        self, username: str, password: str, display_name: str = ""
    ) -> dict:
        """POST /api/users/register"""
        r = await self._client._request(
            "POST", "/api/users/register",
            json_data={
                "username": username,
                "password": password,
                "display_name": display_name or username,
            },
        )
        return r.json()

    async def login(self, username: str, password: str) -> dict:
        """POST /api/users/login — returns user + api_key."""
        r = await self._client._request(
            "POST", "/api/users/login",
            json_data={"username": username, "password": password},
        )
        return r.json()

    async def logout(self) -> dict:
        """POST /api/users/logout"""
        r = await self._client._request("POST", "/api/users/logout")
        return r.json()

    async def me(self) -> dict:
        """GET /api/users/me"""
        r = await self._client._request("GET", "/api/users/me")
        return r.json()

    async def rotate_key(self) -> dict:
        """POST /api/users/me/rotate-key"""
        r = await self._client._request("POST", "/api/users/me/rotate-key")
        return r.json()

    async def list_keys(self) -> list[dict]:
        """GET /api/users/me/keys"""
        r = await self._client._request("GET", "/api/users/me/keys")
        return r.json()

    async def create_key(self, name: str) -> dict:
        """POST /api/users/me/keys"""
        r = await self._client._request(
            "POST", "/api/users/me/keys",
            json_data={"name": name},
        )
        return r.json()

    async def delete_key(self, key_id: str) -> dict:
        """DELETE /api/users/me/keys/{key_id}"""
        r = await self._client._request("DELETE", f"/api/users/me/keys/{key_id}")
        return r.json()


class ServersAPI:
    """Ollama server pool management."""

    def __init__(self, client: VivianClient):
        self._client = client

    async def list(self) -> list[dict]:
        """GET /api/admin/servers"""
        r = await self._client._request("GET", "/api/admin/servers")
        return r.json()

    async def add(
        self, name: str, url: str, max_connections: int = 3, priority: int = 1
    ) -> dict:
        """POST /api/admin/servers"""
        r = await self._client._request(
            "POST", "/api/admin/servers",
            json_data={
                "name": name,
                "url": url,
                "max_connections": max_connections,
                "priority": priority,
            },
        )
        return r.json()

    async def get(self, server_id: str) -> dict:
        """GET /api/admin/servers/{server_id}"""
        r = await self._client._request("GET", f"/api/admin/servers/{server_id}")
        return r.json()

    async def update(self, server_id: str, **fields) -> dict:
        """PATCH /api/admin/servers/{server_id}"""
        r = await self._client._request(
            "PATCH", f"/api/admin/servers/{server_id}", json_data=fields
        )
        return r.json()

    async def delete(self, server_id: str) -> dict:
        """DELETE /api/admin/servers/{server_id}"""
        r = await self._client._request("DELETE", f"/api/admin/servers/{server_id}")
        return r.json()

    async def check(self, server_id: str) -> dict:
        """POST /api/admin/servers/{server_id}/check"""
        r = await self._client._request(
            "POST", f"/api/admin/servers/{server_id}/check"
        )
        return r.json()


class MemoryAPI:
    """Core and episodic memory management."""

    def __init__(self, client: VivianClient):
        self._client = client

    # Core memory
    async def list_core(self, category: Optional[str] = None) -> list[dict]:
        params = {}
        if category:
            params["category"] = category
        r = await self._client._request("GET", "/api/admin/memory/core", params=params)
        return r.json()

    async def create_core(
        self, category: str, key: str, value: str, importance: int = 5
    ) -> dict:
        r = await self._client._request(
            "POST", "/api/admin/memory/core",
            json_data={
                "category": category,
                "key": key,
                "value": value,
                "importance": importance,
            },
        )
        return r.json()

    async def update_core(self, memory_id: str, **fields) -> dict:
        r = await self._client._request(
            "PATCH", f"/api/admin/memory/core/{memory_id}", json_data=fields
        )
        return r.json()

    async def delete_core(self, memory_id: str) -> dict:
        r = await self._client._request(
            "DELETE", f"/api/admin/memory/core/{memory_id}"
        )
        return r.json()

    # Episodic memory
    async def list_episodic(
        self, user_id: Optional[str] = None, limit: int = 50
    ) -> list[dict]:
        params = {"limit": limit}
        if user_id:
            params["user_id"] = user_id
        r = await self._client._request(
            "GET", "/api/admin/memory/episodic", params=params
        )
        return r.json()

    async def create_episodic(
        self,
        content: str,
        user_id: Optional[str] = None,
        importance: int = 4,
        tags: Optional[list[str]] = None,
        summary: str = "",
    ) -> dict:
        body: dict[str, Any] = {
            "content": content,
            "importance": importance,
            "summary": summary,
        }
        if user_id:
            body["user_id"] = user_id
        if tags:
            body["tags"] = tags
        r = await self._client._request(
            "POST", "/api/admin/memory/episodic", json_data=body
        )
        return r.json()

    async def delete_episodic(self, memory_id: str) -> dict:
        r = await self._client._request(
            "DELETE", f"/api/admin/memory/episodic/{memory_id}"
        )
        return r.json()


class EmotionAPI:
    """Emotional state management."""

    def __init__(self, client: VivianClient):
        self._client = client

    async def current(self) -> dict:
        r = await self._client._request("GET", "/api/admin/emotion/current")
        return r.json()

    async def history(self, limit: int = 20) -> list[dict]:
        r = await self._client._request(
            "GET", "/api/admin/emotion/history", params={"limit": limit}
        )
        return r.json()


class ConfigAPI:
    """Vivian configuration."""

    def __init__(self, client: VivianClient):
        self._client = client

    async def get(self) -> dict:
        r = await self._client._request("GET", "/api/admin/config")
        return r.json()

    async def update(self, **fields) -> dict:
        r = await self._client._request(
            "PATCH", "/api/admin/config", json_data=fields
        )
        return r.json()


class StatsAPI:
    """System statistics."""

    def __init__(self, client: VivianClient):
        self._client = client

    async def get(self) -> dict:
        r = await self._client._request("GET", "/api/admin/stats")
        return r.json()


class NewsAPI:
    """News/RSS feed management."""

    def __init__(self, client: VivianClient):
        self._client = client

    async def categories(self) -> list[str]:
        r = await self._client._request("GET", "/api/admin/news/categories")
        return r.json()

    async def sources(self) -> list[dict]:
        r = await self._client._request("GET", "/api/admin/news/sources")
        return r.json()

    async def stats(self) -> dict:
        r = await self._client._request("GET", "/api/admin/news/stats")
        return r.json()

    async def fetch(self) -> dict:
        r = await self._client._request("POST", "/api/admin/news/fetch")
        return r.json()

    async def articles(
        self, category: Optional[str] = None, limit: int = 50
    ) -> list[dict]:
        params: dict[str, Any] = {"limit": min(limit, 200)}
        if category:
            params["category"] = category
        r = await self._client._request(
            "GET", "/api/admin/news/articles", params=params
        )
        return r.json()

    async def search(
        self, query: str, category: Optional[str] = None, limit: int = 20
    ) -> list[dict]:
        params: dict[str, Any] = {"q": query, "limit": min(limit, 100)}
        if category:
            params["category"] = category
        r = await self._client._request(
            "GET", "/api/admin/news/search", params=params
        )
        return r.json()


class LogsAPI:
    """Request log management."""

    def __init__(self, client: VivianClient):
        self._client = client

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        path: Optional[str] = None,
        method: Optional[str] = None,
        model: Optional[str] = None,
        username: Optional[str] = None,
    ) -> list[dict]:
        params: dict[str, Any] = {"limit": min(limit, 500), "offset": offset}
        if path:
            params["path"] = path
        if method:
            params["method"] = method
        if model:
            params["model"] = model
        if username:
            params["username"] = username
        r = await self._client._request("GET", "/api/admin/logs", params=params)
        return r.json()

    async def stats(self) -> dict:
        r = await self._client._request("GET", "/api/admin/logs/stats")
        return r.json()

    async def tokens_by_model(self) -> dict:
        r = await self._client._request("GET", "/api/admin/logs/tokens-by-model")
        return r.json()

    async def clear(self) -> dict:
        r = await self._client._request("DELETE", "/api/admin/logs/clear")
        return r.json()
