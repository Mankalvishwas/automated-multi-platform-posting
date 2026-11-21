"""FastAPI application for the automated multi-platform posting system."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI

from app.schemas import PlatformResult, PostingRequest, PostingResponse
from app.services import posting_service
from app.utils.validators import extract_links

app = FastAPI(
    title="Automated Multi-Platform Posting API",
    version="1.0.0",
    description=(
        "Publish a validated short message to several third-party platforms "
        "in one request. Platform selection is handled by the server; every "
        "platform returns its own result so one failure cannot block the rest."
    ),
)


@app.post(
    "/posting",
    response_model=PostingResponse,
    tags=["posting"],
    summary="Publish a message to all configured platforms",
    responses={
        200: {"description": "Per-platform results (partial success is possible)."},
        422: {"description": "Validation error (length, missing/multiple/invalid CTA link)."},
    },
)
async def create_post(payload: PostingRequest) -> PostingResponse:
    # The request model already guarantees exactly one valid CTA link.
    cta_url = extract_links(payload.message)[0]

    results = [
        PlatformResult.model_validate(asdict(result))
        for result in await posting_service.post_to_all(payload.message, cta_url)
    ]

    return PostingResponse(
        success=any(result.status == "success" for result in results),
        results=results,
    )
