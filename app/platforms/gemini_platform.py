"""LLM platform integration: Google Gemini (generateContent API).

LLM platforms accept a message through their API but do not create a
publicly addressable post.  We therefore report ``public_access=False`` and
``posted_url=None`` for a successful interaction instead of inventing a URL.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.platforms.base import (
    BasePlatform,
    PostResult,
    failure_result,
    sanitize_error,
    success_result,
)

logger = logging.getLogger(__name__)


class GeminiPlatform(BasePlatform):
    name = "Gemini (LLM)"
    required_config = ("GEMINI_API_KEY", "GEMINI_MODEL")

    def is_configured(self) -> bool:
        return bool(settings.GEMINI_API_KEY and settings.GEMINI_MODEL)

    def secrets(self) -> list[str]:
        return [settings.GEMINI_API_KEY]

    async def post(self, message: str, cta_url: str) -> PostResult:
        try:
            from google import genai

            client = genai.Client(
                api_key=settings.GEMINI_API_KEY,
                http_options={"timeout": int(self.timeout * 1000)},
            )
            prompt = (
                "Treat the following as a public announcement. Confirm receipt "
                "and keep the CTA link unchanged.\n\n" + message
            )
            # Hard outer bound: SDK-level retries must never block /posting.
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                ),
                timeout=self.timeout,
            )
        except Exception as error:
            return failure_result(self.name, sanitize_error(error, self.secrets()))

        # Gemini accepts and processes the message but does not create a public
        # post, so `posted_url` stays null and `public_access` is false.
        logger.info(
            "Gemini accepted announcement (response id: %s)",
            getattr(response, "response_id", "unknown"),
        )
        return success_result(self.name, posted_url=None, public_access=False)
