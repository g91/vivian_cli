"""OAuthFlowStep — mirrors src/commands/install-github-app/OAuthFlowStep.tsx."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ...services.analytics.index import log_event
from ...services.oauth.index import OAuthService

PASTE_HERE_MSG = "Paste code here if prompted > "

OAuthStateName = Literal[
    "starting",
    "waiting_for_login",
    "processing",
    "success",
    "error",
    "about_to_retry",
]


@dataclass
class OAuthStatus:
    state: OAuthStateName
    url: str | None = None
    token: str | None = None
    message: str | None = None
    next_state: "OAuthStatus | None" = None


class OAuthFlowController:
    def __init__(self) -> None:
        self.oauth_service = OAuthService()
        self.oauth_status = OAuthStatus(state="starting")
        self.pasted_code = ""
        self.show_paste_prompt = False
        self.url_copied = False

    async def start(self) -> str:
        self.oauth_status = OAuthStatus(state="starting")
        try:
            async def auth_url_handler(url: str) -> None:
                self.oauth_status = OAuthStatus(state="waiting_for_login", url=url)
                self.show_paste_prompt = True

            result = await self.oauth_service.startOAuthFlow(
                auth_url_handler,
                {
                    "login_with_vivian_ai": True,
                    "inference_only": True,
                    "expires_in": 365 * 24 * 60 * 60,
                },
            )
            self.oauth_status = OAuthStatus(state="processing")
            token = result.get("accessToken") or result.get("access_token")
            if not token:
                raise RuntimeError("OAuth flow completed without an access token")
            self.oauth_status = OAuthStatus(state="success", token=token)
            return token
        except Exception as error:
            self.oauth_status = OAuthStatus(
                state="error",
                message=str(error),
                next_state=OAuthStatus(state="starting"),
            )
            log_event("tengu_oauth_error", {"error": str(error)})
            raise

    def submit_manual_code(self, value: str) -> dict:
        authorization_code, _, state = value.partition("#")
        if not authorization_code or not state:
            self.oauth_status = OAuthStatus(
                state="error",
                message="Invalid code. Please make sure the full code was copied",
                next_state=OAuthStatus(state="waiting_for_login", url=self.oauth_status.url),
            )
            return {"ok": False, "error": self.oauth_status.message}
        log_event("tengu_oauth_manual_entry", {})
        return {"ok": True, "authorization_code": authorization_code, "state": state}

    def retry(self) -> None:
        next_state = self.oauth_status.next_state or OAuthStatus(state="starting")
        self.oauth_status = OAuthStatus(state="about_to_retry", next_state=next_state)

    def render(self) -> dict:
        return {
            "title": "Create Authentication Token",
            "subtitle": "Creating a long-lived token for GitHub Actions",
            "status": self.oauth_status.state,
            "message": self.oauth_status.message,
            "url": self.oauth_status.url,
            "show_paste_prompt": self.show_paste_prompt,
            "paste_prompt": PASTE_HERE_MSG if self.show_paste_prompt else None,
            "url_copied": self.url_copied,
            "token": self.oauth_status.token,
        }


def oauth_flow_step() -> OAuthFlowController:
    return OAuthFlowController()
