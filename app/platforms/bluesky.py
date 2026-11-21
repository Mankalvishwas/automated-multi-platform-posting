"""Bluesky integration via AT Protocol XRPC.

1. com.atproto.server.createSession -> access token + DID
2. com.atproto.repo.createRecord   -> app.bsky.feed.post record
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.config import settings
from app.platforms.base import (
    BasePlatform,
    PostResult,
    failure_result,
    sanitize_error,
    success_result,
)


class BlueskyPlatform(BasePlatform):
    name = "Bluesky"
    required_config = ("BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD")

    def is_configured(self) -> bool:
        return bool(
            settings.BLUESKY_HANDLE
            and settings.BLUESKY_APP_PASSWORD
            and settings.BLUESKY_SERVICE_URL.startswith("https://")
        )

    def secrets(self) -> list[str]:
        return [settings.BLUESKY_APP_PASSWORD]

    async def post(self, message: str, cta_url: str) -> PostResult:
        service = settings.BLUESKY_SERVICE_URL
        secrets = self.secrets()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                session_response = await client.post(
                    f"{service}/xrpc/com.atproto.server.createSession",
                    json={
                        "identifier": settings.BLUESKY_HANDLE,
                        "password": settings.BLUESKY_APP_PASSWORD,
                    },
                )
                session_response.raise_for_status()
                session = session_response.json()

                access_token = session["accessJwt"]
                secrets.append(access_token)
                did = session["did"]

                created_at = (
                    datetime.now(timezone.utc)
                    .isoformat(timespec="milliseconds")
                    .replace("+00:00", "Z")
                )
                record: dict = {
                    "$type": "app.bsky.feed.post",
                    "text": message,
                    "createdAt": created_at,
                }

                # Make the CTA clickable by adding a richtext link facet.
                start = message.find(cta_url)
                if start >= 0:
                    end = start + len(cta_url)
                    record["facets"] = [
                        {
                            "index": {
                                "byteStart": len(message[:start].encode("utf-8")),
                                "byteEnd": len(message[:end].encode("utf-8")),
                            },
                            "features": [
                                {
                                    "$type": "app.bsky.richtext.facet#link",
                                    "uri": cta_url,
                                }
                            ],
                        }
                    ]

                create_response = await client.post(
                    f"{service}/xrpc/com.atproto.repo.createRecord",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={
                        "repo": did,
                        "collection": "app.bsky.feed.post",
                        "record": record,
                    },
                )
                create_response.raise_for_status()
                uri = create_response.json()["uri"]

            rkey = uri.rsplit("/", 1)[-1]
            handle = session.get("handle") or settings.BLUESKY_HANDLE
            posted_url = f"https://bsky.app/profile/{handle}/post/{rkey}"

            return success_result(self.name, posted_url=posted_url, public_access=True)
        except Exception as error:
            return failure_result(self.name, sanitize_error(error, secrets))
