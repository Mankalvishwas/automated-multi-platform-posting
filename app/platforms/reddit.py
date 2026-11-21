"""Reddit integration: OAuth2 (script app) + POST /api/submit."""

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

_USER_AGENT = "python:multi-platform-posting:v1.0.0 (by /u/posting-api)"


class RedditPlatform(BasePlatform):
    name = "Reddit"
    required_config = (
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "REDDIT_USERNAME",
        "REDDIT_PASSWORD",
    )

    def is_configured(self) -> bool:
        return all(
            [
                settings.REDDIT_CLIENT_ID,
                settings.REDDIT_CLIENT_SECRET,
                settings.REDDIT_USERNAME,
                settings.REDDIT_PASSWORD,
                settings.REDDIT_SUBREDDIT,
            ]
        )

    def secrets(self) -> list[str]:
        return [
            settings.REDDIT_CLIENT_ID,
            settings.REDDIT_CLIENT_SECRET,
            settings.REDDIT_PASSWORD,
        ]

    async def post(self, message: str, cta_url: str) -> PostResult:
        secrets = self.secrets()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                token_response = await client.post(
                    "https://www.reddit.com/api/v1/access_token",
                    data={
                        "grant_type": "password",
                        "username": settings.REDDIT_USERNAME,
                        "password": settings.REDDIT_PASSWORD,
                    },
                    auth=(settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET),
                    headers={"User-Agent": _USER_AGENT},
                )
                token_response.raise_for_status()
                access_token = token_response.json()["access_token"]
                secrets.append(access_token)

                title = message[:80].rstrip()
                submit_response = await client.post(
                    "https://oauth.reddit.com/api/submit",
                    headers={
                        "Authorization": f"bearer {access_token}",
                        "User-Agent": _USER_AGENT,
                    },
                    data={
                        "api_type": "json",
                        "kind": "self",
                        "sr": settings.REDDIT_SUBREDDIT,
                        "title": title,
                        "text": message,
                    },
                )
                submit_response.raise_for_status()
                payload = submit_response.json().get("json", {})

            errors = payload.get("errors") or []
            if errors:
                raise ValueError(f"Reddit rejected the post: {errors}")

            path = payload.get("data", {}).get("url")
            if not path:
                raise ValueError("Reddit response did not contain a permalink.")

            posted_url = (
                path if path.startswith("http") else f"https://www.reddit.com{path}"
            )
            return success_result(self.name, posted_url=posted_url, public_access=True)
        except Exception as error:
            return failure_result(self.name, sanitize_error(error, secrets))
