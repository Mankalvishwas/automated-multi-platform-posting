"""Shared contract for every third-party posting integration."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from app.config import settings

_BEARER_PATTERN = re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.IGNORECASE)


@dataclass(frozen=True)
class PostResult:
    """Internal, framework-agnostic result produced by a platform adapter."""

    platform: str
    status: str = "failed"
    posted_url: Optional[str] = None
    public_access: bool = False
    date: Optional[str] = None
    time: Optional[str] = None
    error: Optional[str] = None


def _now() -> tuple[str, str]:
    current = datetime.now()
    return current.strftime("%Y-%m-%d"), current.strftime("%H:%M:%S")


def success_result(
    platform: str, posted_url: Optional[str], public_access: bool
) -> PostResult:
    date, time = _now()
    return PostResult(
        platform=platform,
        status="success",
        posted_url=posted_url,
        public_access=public_access,
        date=date,
        time=time,
        error=None,
    )


def failure_result(platform: str, error: str) -> PostResult:
    return PostResult(
        platform=platform,
        status="failed",
        posted_url=None,
        public_access=False,
        date=None,
        time=None,
        error=error[:500],
    )


def sanitize_error(error: BaseException, secrets: Iterable[str] = ()) -> str:
    """Build a safe error string; never echo credentials back to the client."""

    text = f"{type(error).__name__}: {error}"
    for secret in secrets:
        if secret and len(secret) >= 4:
            text = text.replace(secret, "***")
    text = _BEARER_PATTERN.sub(r"\1***", text)
    return text[:500]


class BasePlatform(ABC):
    """Each adapter owns its own configuration check, API call and errors."""

    name: str = "Unknown"
    required_config: tuple[str, ...] = ()

    def __init__(self, timeout: float | None = None) -> None:
        self.timeout = float(timeout if timeout is not None else settings.REQUEST_TIMEOUT)

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True only when all required credentials are present."""

    @abstractmethod
    async def post(self, message: str, cta_url: str) -> PostResult:
        """Publish *message* through the platform API."""

    def missing_config_result(self, missing: Iterable[str] | None = None) -> PostResult:
        names = ", ".join(missing if missing is not None else self.required_config)
        return failure_result(self.name, f"Missing credentials: {names}")

    def secrets(self) -> list[str]:
        """Secret values to redact from any error message (override in adapters)."""

        return []
