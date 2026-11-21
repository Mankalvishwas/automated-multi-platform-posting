"""DEV Community (Forem) integration: POST /api/articles."""

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


class DevToPlatform(BasePlatform):
    name = "DEV Community"
    required_config = ("DEVTO_API_KEY",)

    def is_configured(self) -> bool:
        return bool(settings.DEVTO_API_KEY)

    def secrets(self) -> list[str]:
        return [settings.DEVTO_API_KEY]

    async def post(self, message: str, cta_url: str) -> PostResult:
        # DEV requires a title; derive a short one from the announcement.
        title = message[:70].rstrip()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://dev.to/api/articles",
                    headers={"api-key": settings.DEVTO_API_KEY},
                    json={
                        "article": {
                            "title": title,
                            "body": message,
                            "tags": [],
                            "published": True,
                        }
                    },
                )
                response.raise_for_status()
                data = response.json()

            posted_url = data.get("url")
            if not posted_url:
                raise ValueError("DEV response did not contain an article URL.")

            return success_result(
                self.name,
                posted_url=posted_url,
                public_access=bool(data.get("published", True)),
            )
        except Exception as error:
            return failure_result(self.name, sanitize_error(error, self.secrets()))
