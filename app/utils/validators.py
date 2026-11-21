"""Validation helpers for the posting API request model.

The rules implemented here are shared by the API layer and the tests:

* a message may contain at most 200 characters,
* it must contain exactly one call-to-action (CTA) link,
* that link must be a syntactically valid public http/https URL.

DNS resolution and reachability checks are deliberately *not* performed here:
validation must stay deterministic and work offline.  Reachability is the
responsibility of the individual platform integrations.
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

from pydantic import ValidationError
from pydantic import HttpUrl

# Stops at whitespace and characters that are not part of a URL in plain text.
_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_TRAILING_PUNCTUATION = ".,;:!?)]}"


def extract_links(message: str) -> list[str]:
    """Return every http/https URL found in *message* (deduplication is not done)."""

    return [
        match.group(0).rstrip(_TRAILING_PUNCTUATION)
        for match in _URL_PATTERN.finditer(message)
    ]


def _is_public_host(host: str) -> bool:
    """Reject localhost-style hosts and private/link-local IP literals."""

    host = host.lower().rstrip(".")
    if host in {"localhost"} or host.endswith(".localhost") or host.endswith(".local"):
        return False

    try:
        ip = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        # A domain name. Require a dot so single-label intranet names are rejected.
        return "." in host

    return ip.is_global


def validate_cta_link(message: str) -> str:
    """Validate that *message* contains exactly one usable CTA link.

    Returns the link so callers do not have to run the regex twice.
    Raises ``ValueError`` with a human-readable message on invalid input.
    """

    links = extract_links(message)

    if len(links) == 0:
        raise ValueError(
            "Message must include exactly one CTA link; no http/https link was found."
        )
    if len(links) > 1:
        raise ValueError(
            f"Message must include exactly one CTA link; found {len(links)} links."
        )

    link = links[0]

    try:
        parsed = HttpUrl(link)
    except ValidationError as error:
        raise ValueError(f"The CTA link '{link}' is not a valid http/https URL.") from error

    host = urlparse(link).hostname or ""
    if not host or not _is_public_host(host):
        raise ValueError(
            "The CTA link must point to a public host (localhost, private and "
            "single-label addresses are not allowed)."
        )

    return link
