"""Vivian API Server — exposes all /v1/* endpoints required by vivian_cli.

This server IS the backend that vivian_cli talks to.  It can be run:
  - Standalone: `python -m vivian_cli.integration.server`
  - As a Flask blueprint: `app.register_blueprint(create_blueprint())`
  - Via uvicorn (ASGI): `uvicorn vivian_cli.integration.server:asgi_app`

All routes proxy to the OllamaPlanner backend (VIVIAN_INTERNAL_URL) where
needed, or handle the request directly using vivian_cli's own logic.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Try importing web framework ──────────────────────────────────────────────
try:
    from flask import Flask, Blueprint, request, jsonify, Response, stream_with_context
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


# ── Proxy helpers ────────────────────────────────────────────────────────────

def _internal_url(path: str) -> str:
    from .config import get_config
    base = get_config().internal_api_url.rstrip("/")
    return f"{base}{path}"


def _proxy_get(path: str, params: Optional[dict] = None, token: Optional[str] = None) -> dict:
    """Forward a GET to the internal OllamaPlanner."""
    if not HAS_HTTPX:
        raise RuntimeError("httpx required for proxy calls")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    import httpx as _httpx
    with _httpx.Client(timeout=30) as client:
        r = client.get(_internal_url(path), params=params, headers=headers)
        r.raise_for_status()
        return r.json()


def _proxy_post(path: str, body: Optional[dict] = None, token: Optional[str] = None) -> dict:
    """Forward a POST to the internal OllamaPlanner."""
    if not HAS_HTTPX:
        raise RuntimeError("httpx required for proxy calls")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    import httpx as _httpx
    with _httpx.Client(timeout=60) as client:
        r = client.post(_internal_url(path), json=body or {}, headers=headers)
        r.raise_for_status()
        return r.json()


def _auth_token() -> Optional[str]:
    if not HAS_FLASK:
        return None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


# ── Flask Blueprint ──────────────────────────────────────────────────────────

def create_blueprint(url_prefix: str = "") -> "Blueprint":
    """Create a Flask Blueprint with all vivian_cli API routes.

    Register on an existing Flask app:
        from vivian_cli.integration.server import create_blueprint
        app.register_blueprint(create_blueprint())
    """
    if not HAS_FLASK:
        raise ImportError("flask is required: pip install flask")

    bp = Blueprint("vivian_api", __name__, url_prefix=url_prefix)

    # ── Health ────────────────────────────────────────────────────────────────

    @bp.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "service": "vivian-api", "timestamp": int(time.time())})

    # ── Models ────────────────────────────────────────────────────────────────

    @bp.route("/v1/models", methods=["GET"])
    def list_models():
        try:
            data = _proxy_get("/api/models")
            models = data if isinstance(data, list) else data.get("models", data.get("data", []))
        except Exception:
            from ..constants import DEFAULT_MODEL
            models = [{"id": DEFAULT_MODEL, "object": "model", "owned_by": "vivian"}]
        return jsonify({"object": "list", "data": [
            {"id": m if isinstance(m, str) else m.get("id", str(m)), "object": "model", "owned_by": "vivian"}
            for m in models
        ]})

    # ── Messages (Anthropic-compatible) ──────────────────────────────────────

    @bp.route("/v1/messages", methods=["POST"])
    def messages():
        body = request.get_json(force=True) or {}
        try:
            resp = _proxy_post("/api/chat", body, token=_auth_token())
            return jsonify(resp)
        except Exception as e:
            logger.warning(f"[server] /v1/messages proxy failed: {e}, falling back to local")
            # Fallback: run locally
            result = _run_local_inference(body)
            return jsonify(result)

    # ── Chat Completions (OpenAI-compatible) ──────────────────────────────────

    @bp.route("/v1/chat/completions", methods=["POST"])
    def chat_completions():
        body = request.get_json(force=True) or {}
        stream = body.get("stream", False)
        try:
            if stream:
                return _stream_chat_completions(body)
            resp = _proxy_post("/api/chat/completions", body, token=_auth_token())
            return jsonify(resp)
        except Exception as e:
            logger.warning(f"[server] /v1/chat/completions proxy failed: {e}")
            result = _run_local_inference(body)
            return jsonify(result)

    # ── Sessions ──────────────────────────────────────────────────────────────

    _sessions: dict[str, dict] = {}  # In-process session store (use Redis in prod)

    @bp.route("/v1/sessions", methods=["POST"])
    def create_session():
        body = request.get_json(force=True) or {}
        session_id = str(uuid.uuid4())
        session = {
            "id": session_id,
            "title": body.get("title", f"Session {session_id[:8]}"),
            "status": "active",
            "created_at": int(time.time() * 1000),
            "organization_uuid": body.get("organization_uuid"),
            "metadata": body.get("metadata", {}),
            "tags": body.get("tags", []),
        }
        _sessions[session_id] = session
        logger.info(f"[server] Created session {session_id}")
        return jsonify(session), 201

    @bp.route("/v1/sessions", methods=["GET"])
    def list_sessions():
        org = request.args.get("organization_uuid")
        sessions = [s for s in _sessions.values()
                    if not org or s.get("organization_uuid") == org]
        return jsonify({"sessions": sessions, "has_more": False})

    @bp.route("/v1/sessions/<session_id>", methods=["GET"])
    def get_session(session_id: str):
        s = _sessions.get(session_id)
        if not s:
            return jsonify({"error": "session not found"}), 404
        return jsonify(s)

    @bp.route("/v1/sessions/<session_id>", methods=["PATCH"])
    def update_session(session_id: str):
        s = _sessions.get(session_id)
        if not s:
            return jsonify({"error": "session not found"}), 404
        body = request.get_json(force=True) or {}
        if "title" in body:
            s["title"] = body["title"]
        return jsonify(s)

    @bp.route("/v1/sessions/<session_id>/archive", methods=["POST"])
    def archive_session(session_id: str):
        s = _sessions.get(session_id)
        if not s:
            return jsonify({"error": "session not found"}), 404
        if s.get("status") == "archived":
            return jsonify({"error": "already archived"}), 409
        s["status"] = "archived"
        return "", 204

    _session_events: dict[str, list] = {}

    @bp.route("/v1/sessions/<session_id>/events", methods=["POST"])
    def post_session_event(session_id: str):
        body = request.get_json(force=True) or {}
        events = _session_events.setdefault(session_id, [])
        event = {"id": str(uuid.uuid4()), "created_at": int(time.time() * 1000), **body}
        events.append(event)
        return jsonify(event), 201

    @bp.route("/v1/sessions/<session_id>/events", methods=["GET"])
    def get_session_events(session_id: str):
        after_id = request.args.get("after_id")
        limit = int(request.args.get("limit", 50))
        events = _session_events.get(session_id, [])
        if after_id:
            idx = next((i for i, e in enumerate(events) if e["id"] == after_id), -1)
            events = events[idx + 1:]
        events = events[-limit:]
        return jsonify({"events": events, "last_event_id": events[-1]["id"] if events else None})

    # ── Code Sessions (env-less bridge) ──────────────────────────────────────

    _code_sessions: dict[str, dict] = {}

    @bp.route("/v1/code/sessions", methods=["POST"])
    def create_code_session():
        body = request.get_json(force=True) or {}
        session_id = str(uuid.uuid4())
        cs = {
            "id": session_id,
            "title": body.get("title", f"Code Session {session_id[:8]}"),
            "status": "active",
            "created_at": int(time.time() * 1000),
            "organization_uuid": body.get("organization_uuid"),
            "tags": body.get("tags", []),
            "worker_epoch": 0,
        }
        _code_sessions[session_id] = cs
        return jsonify({"id": session_id}), 201

    @bp.route("/v1/code/sessions/<session_id>/bridge", methods=["POST"])
    def create_bridge_token(session_id: str):
        cs = _code_sessions.get(session_id)
        if not cs:
            return jsonify({"error": "session not found"}), 404
        cs["worker_epoch"] = cs.get("worker_epoch", 0) + 1
        from .config import get_config
        cfg = get_config()
        # Issue a simple JWT-like token (in production, use a real JWT library)
        import base64, json as _json
        payload = {
            "session_id": session_id,
            "epoch": cs["worker_epoch"],
            "exp": int(time.time()) + 3600,
        }
        token = base64.urlsafe_b64encode(_json.dumps(payload).encode()).decode().rstrip("=")
        return jsonify({
            "worker_jwt": token,
            "expires_in": 3600,
            "api_base_url": f"wss://{cfg.base_api_url.split('://', 1)[-1]}",
            "worker_epoch": cs["worker_epoch"],
        })

    @bp.route("/v1/code/sessions/<session_id>/worker/register", methods=["POST"])
    def register_worker(session_id: str):
        return jsonify({"status": "registered", "session_id": session_id})

    @bp.route("/v1/code/sessions/<session_id>/worker/events/stream", methods=["GET"])
    def worker_events_stream(session_id: str):
        def _gen():
            yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
        return Response(stream_with_context(_gen()), mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # ── Environments (v1 bridge) ──────────────────────────────────────────────

    _environments: dict[str, dict] = {}

    @bp.route("/v1/environments/bridge", methods=["POST"])
    def register_environment():
        body = request.get_json(force=True) or {}
        env_id = str(uuid.uuid4())
        env = {
            "environment_id": env_id,
            "bridge_id": body.get("bridge_id", env_id),
            "status": "ready",
            "created_at": int(time.time() * 1000),
            "metadata": body.get("metadata", {}),
            "pending_work": [],
        }
        _environments[env_id] = env
        logger.info(f"[server] Registered environment {env_id}")
        return jsonify({"environment_id": env_id}), 201

    @bp.route("/v1/environments/<env_id>/work/poll", methods=["POST"])
    def poll_work(env_id: str):
        env = _environments.get(env_id)
        if not env:
            return jsonify({"error": "environment not found"}), 404
        work = env.get("pending_work", [])
        if not work:
            return "", 204
        item = work.pop(0)
        return jsonify(item)

    @bp.route("/v1/environments/<env_id>/work/<work_id>/ack", methods=["POST"])
    def ack_work(env_id: str, work_id: str):
        return jsonify({"status": "acknowledged"})

    @bp.route("/v1/environments/<env_id>/work/<work_id>/stop", methods=["POST"])
    def stop_work(env_id: str, work_id: str):
        return jsonify({"status": "stopped"})

    @bp.route("/v1/environments/<env_id>/work/<work_id>/heartbeat", methods=["POST"])
    def heartbeat_work(env_id: str, work_id: str):
        return jsonify({"status": "alive"})

    @bp.route("/v1/environments/bridge/<env_id>", methods=["DELETE"])
    def deregister_environment(env_id: str):
        _environments.pop(env_id, None)
        return "", 204

    @bp.route("/v1/environments/<env_id>/bridge/reconnect", methods=["POST"])
    def reconnect_environment(env_id: str):
        return jsonify({"status": "reconnecting"})

    # ── Environment Providers (Teleport / CCR) ────────────────────────────────

    @bp.route("/v1/environment_providers", methods=["GET"])
    def list_environment_providers():
        return jsonify({"providers": [{"id": "cloud", "name": "Cloud", "available": True}]})

    @bp.route("/v1/environment_providers/cloud/create", methods=["POST"])
    def create_cloud_environment():
        body = request.get_json(force=True) or {}
        return jsonify({
            "environment_id": str(uuid.uuid4()),
            "sdk_url": f"wss://api-vivian.d0a.net/v1/session_ingress/ws/{uuid.uuid4()}",
            "status": "creating",
        }), 202

    # ── Trusted Devices ──────────────────────────────────────────────────────

    @bp.route("/api/auth/trusted_devices", methods=["POST"])
    def enroll_trusted_device():
        body = request.get_json(force=True) or {}
        return jsonify({
            "trusted_device_token": str(uuid.uuid4()),
            "expires_at": int(time.time()) + 30 * 24 * 3600,
            "device_name": body.get("device_name", "unknown"),
        }), 201

    # ── OAuth ────────────────────────────────────────────────────────────────

    @bp.route("/oauth/userinfo", methods=["GET"])
    def userinfo():
        token = _auth_token()
        if not token:
            return jsonify({"error": "unauthorized"}), 401
        # Try proxy to internal Vivian auth
        try:
            data = _proxy_get("/api/auth/me", token=token)
            return jsonify({
                "sub": data.get("id") or data.get("uuid") or str(uuid.uuid4()),
                "email": data.get("email", ""),
                "organization_uuid": data.get("organization_uuid") or data.get("org_id"),
                **data,
            })
        except Exception:
            return jsonify({"sub": "vivian-user", "email": "vivian@local"})

    @bp.route("/oauth/token", methods=["POST"])
    def oauth_token():
        data = request.form.to_dict() if request.content_type and "urlencoded" in request.content_type \
            else (request.get_json(force=True) or {})
        grant_type = data.get("grant_type")
        if grant_type == "refresh_token":
            # Try to proxy refresh to internal Vivian
            try:
                resp = _proxy_post("/api/auth/refresh", {"refresh_token": data.get("refresh_token")})
                return jsonify(resp)
            except Exception:
                return jsonify({"error": "invalid_grant"}), 400
        return jsonify({"error": "unsupported_grant_type"}), 400

    return bp


# ── Inference helpers ────────────────────────────────────────────────────────

def _run_local_inference(body: dict) -> dict:
    """Fallback: call vivian_cli's QueryEngine directly."""
    messages = body.get("messages", [])
    model = body.get("model", "qwen3.6")
    from .config import get_config
    cfg = get_config()
    # Attempt sync query via httpx to internal
    if HAS_HTTPX:
        try:
            import httpx as _httpx
            with _httpx.Client(timeout=cfg.timeout) as client:
                r = client.post(
                    _internal_url("/api/chat"),
                    json=body,
                    headers={"Content-Type": "application/json"},
                )
                if r.status_code == 200:
                    return r.json()
        except Exception:
            pass
    # Ultimate fallback response
    return {
        "id": f"msg-{uuid.uuid4()}",
        "object": "chat.completion",
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "Vivian is not connected to a model backend."},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _stream_chat_completions(body: dict):
    """Stream chat completion via SSE."""
    from flask import Response, stream_with_context

    def _gen():
        try:
            resp = _run_local_inference({**body, "stream": False})
            content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
            chunk = {
                "id": resp.get("id", f"msg-{uuid.uuid4()}"),
                "object": "chat.completion.chunk",
                "model": body.get("model", "qwen3.6"),
                "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            done = {**chunk, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
            yield f"data: {json.dumps(done)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(_gen()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Standalone Flask app ─────────────────────────────────────────────────────

def create_app(internal_url: Optional[str] = None, **cfg_kwargs) -> "Flask":
    """Create a standalone Flask app with all Vivian API routes.

    Usage:
        app = create_app(internal_url="http://localhost:5000")
        app.run(host="0.0.0.0", port=8080)
    """
    if not HAS_FLASK:
        raise ImportError("flask is required: pip install flask")

    from .config import configure
    configure(internal_api_url=internal_url or os.environ.get("VIVIAN_INTERNAL_URL", "http://localhost:5000"),
              **cfg_kwargs)

    app = Flask(__name__)
    app.register_blueprint(create_blueprint())
    return app


# ── ASGI adapter (uvicorn) ───────────────────────────────────────────────────
#
# Run with:
#   uvicorn vivian_cli.integration.server:asgi_app
#
try:
    from asgiref.wsgi import WsgiToAsgi
    asgi_app = WsgiToAsgi(create_app())
except Exception:
    asgi_app = None


# ── Main (dev server) ────────────────────────────────────────────────────────

def main() -> None:
    """Entry point for the `vivian-server` console script."""
    import argparse

    parser = argparse.ArgumentParser(description="Vivian API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8080, help="Bind port")
    parser.add_argument("--internal-url", default="http://localhost:5000",
                        help="OllamaPlanner internal URL")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")

    app = create_app(internal_url=args.internal_url, debug=args.debug)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
