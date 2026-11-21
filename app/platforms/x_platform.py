"""X (Twitter) integration: X API v2 POST /2/tweets.

Note: creating Posts requires an X API plan with write access.  When the
token or plan is missing, the adapter reports a normal failure and the other
platforms are still attempted.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.platforms.base import (
    BasePlatform,
    PostResult,
    failure_result,
    sanitize_error,
    success_result,
)


class XPlatform(BasePlatform):
    name = "X (Twitter)"
    required_config = ("X_BEARER_TOKEN",)

    def is_configured(self) -> bool:
        return bool(settings.X_BEARER_TOKEN)

    def secrets(self) -> list[str]:
        return [settings.X_BEARER_TOKEN]

    async def post(self, message: str, cta_url: str) -> PostResult:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.x.com/2/tweets",
                    headers={"Authorization": f"Bearer {settings.X_BEARER_TOKEN}"},
                    json={"text": message},
                )
                response.raise_for_status()
                post_id = response.json()["data"]["id"]

            return success_result(
                self.name,
                posted_url=f"https://x.com/i/web/status/{post_id}",
                public_access=True,
            )
        except Exception as error:
            return failure_result(self.name, sanitize_error(error, self.secrets()))
