"""Orchestration of all configured posting platforms.

Platforms are attempted concurrently and independently: a timeout, an
authentication error or a missing credential on one platform never prevents
the remaining platforms from receiving the message.
"""

from __future__ import annotations

import asyncio
import logging

from app.platforms.base import BasePlatform, PostResult, failure_result, sanitize_error
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.devto import DevToPlatform
from app.platforms.gemini_platform import GeminiPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.reddit import RedditPlatform
from app.platforms.x_platform import XPlatform

logger = logging.getLogger(__name__)


def build_platforms() -> list[BasePlatform]:
    """Return every supported integration (platform choice is server-side)."""

    return [
        GeminiPlatform(),
        MastodonPlatform(),
        BlueskyPlatform(),
        DevToPlatform(),
        RedditPlatform(),
        XPlatform(),
    ]


async def _post_safely(platform: BasePlatform, message: str, cta_url: str) -> PostResult:
    if not platform.is_configured():
        logger.warning("%s skipped: credentials missing", platform.name)
        return platform.missing_config_result()

    try:
        result = await platform.post(message, cta_url)
        logger.info("%s -> %s", platform.name, result.status)
        return result
    except Exception as error:  # last-resort guard: adapters normally handle this
        logger.exception("Unexpected error from %s", platform.name)
        return failure_result(platform.name, sanitize_error(error, platform.secrets()))


async def post_to_all(message: str, cta_url: str) -> list[PostResult]:
    """Post to all platforms and return one result per platform."""

    platforms = build_platforms()
    return list(
        await asyncio.gather(
            *(_post_safely(platform, message, cta_url) for platform in platforms)
        )
    )
