"""OAuth token manager — handles acquiring, refreshing, and caching tokens.

Connects vivian_cli's auth layer to the Vivian platform's OAuth endpoints:
  POST /oauth/token            (code → access+refresh)
  POST /oauth/token (refresh)  (refresh → new access)
  GET  /oauth/userinfo         (token → account info)

Tokens are stored in:
  - Memory cache (fastest, current process)
  - ~/.config/vivian/tokens.json (persisted across CLI invocations)
  - VIVIAN_ACCESS_TOKEN env var (CI/CD override, no storage needed)
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_TOKEN_DIR = Path.home() / ".config" / "vivian"
_TOKEN_FILE = _TOKEN_DIR / "tokens.json"


@dataclass
class TokenSet:
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[int] = None   # Unix ms
    id_token: Optional[str] = None
    account_uuid: Optional[str] = None
    organization_uuid: Optional[str] = None
    email: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return int(time.time() * 1000) >= self.expires_at

    @property
    def needs_refresh(self) -> bool:
        """True when < 5 minutes remain (proactive refresh window)."""
        if self.expires_at is None:
            return False
        return int(time.time() * 1000) >= (self.expires_at - 5 * 60 * 1000)


def _load_tokens() -> Optional[TokenSet]:
    """Load persisted tokens from disk."""
    try:
        data = json.loads(_TOKEN_FILE.read_text())
        return TokenSet(**{k: v for k, v in data.items() if k in TokenSet.__dataclass_fields__})
    except Exception:
        return None


def _save_tokens(ts: TokenSet) -> None:
    """Persist tokens to disk."""
    try:
        _TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        _TOKEN_FILE.write_text(json.dumps(asdict(ts), indent=2))
        _TOKEN_FILE.chmod(0o600)
    except Exception as e:
        logger.warning(f"Could not save tokens: {e}")


def _clear_tokens() -> None:
    try:
        _TOKEN_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _post_token(url: str, data: dict) -> dict:
    """HTTP POST to a token endpoint."""
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=encoded, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _get_userinfo(token_url_base: str, access_token: str) -> dict:
    url = token_url_base.replace("/oauth/token", "/oauth/userinfo")
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


class OAuthManager:
    """Manages the full OAuth lifecycle for Vivian CLI.

    Supports:
      - Env var token (CI/CD — no browser needed)
      - Device/PKCE flow (interactive CLI login)
      - Refresh on expiry
      - Userinfo fetch for org UUID
    """

    def __init__(self):
        self._tokens: Optional[TokenSet] = None
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        # 1. Env var override (highest priority — CI/CD)
        env_token = (
            os.environ.get("VIVIAN_ACCESS_TOKEN")
            or os.environ.get("vivian_BRIDGE_OAUTH_TOKEN")
            or os.environ.get("ANTHROPIC_API_KEY")
        )
        if env_token:
            self._tokens = TokenSet(access_token=env_token)
            return
        # 2. Disk cache
        self._tokens = _load_tokens()

    def get_tokens(self) -> Optional[TokenSet]:
        self._ensure_loaded()
        return self._tokens

    def get_access_token(self) -> Optional[str]:
        self._ensure_loaded()
        ts = self._tokens
        if ts is None:
            return None
        return ts.access_token if ts.access_token else None

    def get_organization_uuid(self) -> Optional[str]:
        self._ensure_loaded()
        return self._tokens.organization_uuid if self._tokens else None

    def set_tokens(self, ts: TokenSet) -> None:
        self._tokens = ts
        _save_tokens(ts)

    def clear_tokens(self) -> None:
        self._tokens = None
        _clear_tokens()

    async def refresh_if_needed(self) -> bool:
        """Refresh access token if it's near expiry. Returns True if refreshed."""
        self._ensure_loaded()
        ts = self._tokens
        if ts is None or not ts.needs_refresh or not ts.refresh_token:
            return False
        try:
            from .config import get_config
            cfg = get_config()
            from ..constants.oauth import get_oauth_config
            oauth = get_oauth_config()
            token_url = oauth["TOKEN_URL"]
            data = {
                "grant_type": "refresh_token",
                "refresh_token": ts.refresh_token,
                "client_id": oauth["CLIENT_ID"],
            }
            resp = _post_token(token_url, data)
            expires_in = resp.get("expires_in", 3600)
            new_ts = TokenSet(
                access_token=resp["access_token"],
                refresh_token=resp.get("refresh_token", ts.refresh_token),
                expires_at=int(time.time() * 1000) + int(expires_in) * 1000,
                id_token=resp.get("id_token", ts.id_token),
                account_uuid=ts.account_uuid,
                organization_uuid=ts.organization_uuid,
                email=ts.email,
            )
            self.set_tokens(new_ts)
            logger.info("[oauth] Token refreshed successfully")
            return True
        except Exception as e:
            logger.warning(f"[oauth] Token refresh failed: {e}")
            return False

    def begin_pkce_login(self) -> tuple[str, str, str]:
        """Generate PKCE params + authorization URL.

        Returns (auth_url, code_verifier, state).
        The caller must open auth_url in the browser and then call
        complete_pkce_login(code, code_verifier) with the callback code.
        """
        from ..constants.oauth import get_oauth_config
        oauth = get_oauth_config()
        code_verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        state = secrets.token_urlsafe(16)
        params = urllib.parse.urlencode({
            "response_type": "code",
            "client_id": oauth["CLIENT_ID"],
            "redirect_uri": oauth["REDIRECT_URI"],
            "scope": oauth.get("SCOPES", "openid profile email offline_access"),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        })
        auth_url = f"{oauth['AUTHORIZE_URL']}?{params}"
        return auth_url, code_verifier, state

    def complete_pkce_login(self, code: str, code_verifier: str) -> TokenSet:
        """Exchange authorization code for tokens. Fetches userinfo too."""
        from ..constants.oauth import get_oauth_config
        oauth = get_oauth_config()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": oauth["CLIENT_ID"],
            "redirect_uri": oauth["REDIRECT_URI"],
            "code_verifier": code_verifier,
        }
        resp = _post_token(oauth["TOKEN_URL"], data)
        expires_in = resp.get("expires_in", 3600)
        ts = TokenSet(
            access_token=resp["access_token"],
            refresh_token=resp.get("refresh_token"),
            expires_at=int(time.time() * 1000) + int(expires_in) * 1000,
            id_token=resp.get("id_token"),
        )
        # Fetch org/account info
        try:
            info = _get_userinfo(oauth["TOKEN_URL"], ts.access_token)
            ts.account_uuid = info.get("sub") or info.get("account_uuid")
            ts.organization_uuid = info.get("organization_uuid") or info.get("org_id")
            ts.email = info.get("email")
        except Exception as e:
            logger.warning(f"[oauth] userinfo fetch failed: {e}")
        self.set_tokens(ts)
        return ts

    def login_with_api_key(self, api_key: str) -> TokenSet:
        """Store a raw API key as the access token (no OAuth flow needed)."""
        ts = TokenSet(access_token=api_key)
        self.set_tokens(ts)
        return ts

    async def fetch_userinfo(self) -> Optional[dict]:
        """Fetch account / organization info from /oauth/userinfo."""
        token = self.get_access_token()
        if not token:
            return None
        try:
            from ..constants.oauth import get_oauth_config
            oauth = get_oauth_config()
            info = _get_userinfo(oauth["TOKEN_URL"], token)
            # Cache the org UUID into current token set
            if self._tokens:
                self._tokens.account_uuid = info.get("sub") or info.get("account_uuid")
                self._tokens.organization_uuid = info.get("organization_uuid") or info.get("org_id")
                self._tokens.email = info.get("email")
                _save_tokens(self._tokens)
            return info
        except Exception as e:
            logger.warning(f"[oauth] userinfo fetch failed: {e}")
            return None


_oauth_manager: Optional[OAuthManager] = None


def get_oauth_manager() -> OAuthManager:
    global _oauth_manager
    if _oauth_manager is None:
        _oauth_manager = OAuthManager()
    return _oauth_manager
