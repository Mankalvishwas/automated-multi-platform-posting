"""Tests for validation, orchestration and the /posting endpoint.

No live API keys are needed: integrations are replaced with deterministic
stubs so the tests are fast and repeatable.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.platforms.base import (
    BasePlatform,
    PostResult,
    failure_result,
    sanitize_error,
    success_result,
)
from app.schemas import PostingRequest
from app.services import posting_service

client = TestClient(app)

VALID_MESSAGE = (
    "Check out our latest business platform and grow your online visibility. "
    "https://example.com"
)


# --------------------------------------------------------------------------
# Input validation
# --------------------------------------------------------------------------


def test_valid_message_is_accepted() -> None:
    request = PostingRequest(message=f"  {VALID_MESSAGE}  ")
    assert request.message == VALID_MESSAGE
    assert len(request.message) <= 200


@pytest.mark.parametrize(
    "message",
    [
        "",
        "   ",
        "a" * 201 + " https://example.com",
        "No link in this announcement at all.",
        "Two links: https://example.com and https://python.org",
        "Bad link: https://",
        "Local link: http://localhost:8000/page",
        "Private link: http://192.168.1.10/admin",
    ],
)
def test_invalid_messages_are_rejected(message: str) -> None:
    with pytest.raises(ValidationError):
        PostingRequest(message=message)


def test_endpoint_returns_422_for_invalid_message() -> None:
    response = client.post("/posting", json={"message": "Missing the CTA link"})
    assert response.status_code == 422
    assert "exactly one CTA link" in response.text


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


class StubPlatform(BasePlatform):
    def __init__(
        self, name: str, *, configured: bool = True, fail: bool = False
    ) -> None:
        super().__init__(timeout=1)
        self.name = name
        self.required_config = ("TEST_TOKEN",)
        self.configured = configured
        self.fail = fail

    def is_configured(self) -> bool:
        return self.configured

    async def post(self, message: str, cta_url: str) -> PostResult:
        if self.fail:
            raise RuntimeError("simulated API outage")
        return success_result(self.name, f"https://example.com/{self.name}", True)


@pytest.mark.asyncio
async def test_one_failure_does_not_stop_other_platforms(monkeypatch) -> None:
    monkeypatch.setattr(
        posting_service,
        "build_platforms",
        lambda: [
            StubPlatform("ok-1"),
            StubPlatform("broken", fail=True),
            StubPlatform("unconfigured", configured=False),
            StubPlatform("ok-2"),
        ],
    )

    results = await posting_service.post_to_all(VALID_MESSAGE, "https://example.com")

    assert [result.platform for result in results] == [
        "ok-1",
        "broken",
        "unconfigured",
        "ok-2",
    ]
    assert [result.status for result in results] == [
        "success",
        "failed",
        "failed",
        "success",
    ]
    assert results[0].posted_url == "https://example.com/ok-1"
    assert results[1].error and "simulated API outage" in results[1].error
    assert results[2].error and "Missing credentials: TEST_TOKEN" in results[2].error
    assert results[3].date and results[3].time


def test_secret_values_are_redacted_from_errors() -> None:
    error = RuntimeError("request failed with Bearer super-secret-token")
    message = sanitize_error(error, ["super-secret-token"])
    assert "super-secret-token" not in message
    assert "***" in message


# --------------------------------------------------------------------------
# HTTP contract
# --------------------------------------------------------------------------


def test_endpoint_returns_expected_shape(monkeypatch) -> None:
    async def fake_post(message: str, cta_url: str) -> list[PostResult]:
        assert message == VALID_MESSAGE
        assert cta_url == "https://example.com"
        return [
            success_result("Platform A", "https://example.com/post/123", True),
            failure_result("Platform B", "Authentication failed"),
        ]

    monkeypatch.setattr(posting_service, "post_to_all", fake_post)

    response = client.post("/posting", json={"message": VALID_MESSAGE})
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert len(body["results"]) == 2

    first, second = body["results"]
    assert first == {
        "platform": "Platform A",
        "status": "success",
        "posted_url": "https://example.com/post/123",
        "public_access": True,
        "date": first["date"],
        "time": first["time"],
        "error": None,
    }
    assert first["date"] and first["time"]
    assert second["status"] == "failed"
    assert second["posted_url"] is None
    assert second["public_access"] is False
    assert second["date"] is None
    assert second["time"] is None
    assert second["error"] == "Authentication failed"


def test_success_is_false_when_every_platform_fails(monkeypatch) -> None:
    async def fake_post(message: str, cta_url: str) -> list[PostResult]:
        return [failure_result("Platform A", "unauthorized")]

    monkeypatch.setattr(posting_service, "post_to_all", fake_post)

    response = client.post("/posting", json={"message": VALID_MESSAGE})
    assert response.status_code == 200
    assert response.json()["success"] is False
