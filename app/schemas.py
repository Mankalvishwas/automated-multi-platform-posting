
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.utils.validators import validate_cta_link


class Competitor(BaseModel):
    name: str
    website: str
    reason: str
    status: str


class SearchQuery(BaseModel):
    query: str
    platform: str
    intent: str
    reason: str


class SEORecommendation(BaseModel):
    priority: str
    area: str
    recommendation: str
    reason: str


class Service(BaseModel):
    name: str
    description: str
    evidence: str


class AudienceAnalysis(BaseModel):
    primary_audience: list[str]
    secondary_audience: list[str]
    audience_needs: list[str]


class WebsiteAnalysis(BaseModel):
    business_summary: str
    competitors: list[Competitor]
    search_queries: list[SearchQuery]
    seo_recommendations: list[SEORecommendation]
    services: list[Service]
    target_audience: AudienceAnalysis
    limitations: list[str]


# --- Multi-platform posting API -------------------------------------------


MAX_MESSAGE_LENGTH = 200


class PostingRequest(BaseModel):
    """Input for ``POST /posting``.

    Platform selection is intentionally not part of this model: the server
    decides which integrations to call.
    """

    message: str = Field(
        ...,
        min_length=1,
        max_length=MAX_MESSAGE_LENGTH,
        description=(
            "Short announcement, at most 200 characters, containing exactly "
            "one public http/https CTA link."
        ),
        examples=[
            "Check out our latest business platform and grow your online "
            "visibility. https://example.com"
        ],
    )

    @field_validator("message", mode="before")
    @classmethod
    def _validate_message(cls, value: object) -> object:
        if not isinstance(value, str):
            return value  # let Pydantic raise the standard type error

        message = value.strip()

        if not message:
            raise ValueError("Message must not be empty.")
        if len(message) > MAX_MESSAGE_LENGTH:
            raise ValueError(
                f"Message must not exceed {MAX_MESSAGE_LENGTH} characters "
                f"(received {len(message)})."
            )

        validate_cta_link(message)
        return message


class PlatformResult(BaseModel):
    """Outcome of one platform integration."""

    platform: str
    status: Literal["success", "failed"]
    posted_url: Optional[str] = None
    public_access: bool = False
    date: Optional[str] = None
    time: Optional[str] = None
    error: Optional[str] = None


class PostingResponse(BaseModel):
    """Aggregate response. ``success`` is true when at least one post worked."""

    success: bool
    results: list[PlatformResult]
