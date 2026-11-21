"""Mastodon integration: POST /api/v1/statuses."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from app.config import settings
from app.platforms.base import (
    BasePlatform,
    PostResult,
    failure_result,
    sanitize_error,
    success_result,
)


class MastodonPlatform(BasePlatform):
    name = "Mastodon"
    required_config = ("MASTODON_BASE_URL", "MASTODON_ACCESS_TOKEN")

    def _base_url(self) -> str:
        return settings.MASTODON_BASE_URL.strip().rstrip("/")

    def is_configured(self) -> bool:
        parsed = urlparse(self._base_url())
        return (
            bool(settings.MASTODON_ACCESS_TOKEN)
            and parsed.scheme in ("http", "https")
            and bool(parsed.netloc)
        )

    def secrets(self) -> list[str]:
        return [settings.MASTODON_ACCESS_TOKEN]

    async def post(self, message: str, cta_url: str) -> PostResult:
        headers = {"Authorization": f"Bearer {settings.MASTODON_ACCESS_TOKEN}"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self._base_url()}/api/v1/statuses",
                    headers=headers,
                    json={"status": message, "visibility": "public"},
                )
                response.raise_for_status()
                data = response.json()

            posted_url = data.get("url") or data.get("uri")
            if not posted_url:
                raise ValueError("Mastodon response did not contain a status URL.")

            return success_result(
                self.name,
                posted_url=posted_url,
                public_access=data.get("visibility", "public") == "public",
            )
        except Exception as error:
            return failure_result(self.name, sanitize_error(error, self.secrets()))
