
import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


def validate_url(url: str) -> str:
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS URLs are allowed.")

    if not parsed.hostname:
        raise ValueError("Invalid website URL.")

    hostname = parsed.hostname.lower()

    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("Localhost URLs are not allowed.")

    try:
        addresses = socket.getaddrinfo(
            hostname, None, type=socket.SOCK_STREAM
        )
    except socket.gaierror:
        raise ValueError("Website address could not be resolved.")

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])

        if not ip.is_global:
            raise ValueError("Private or restricted IP addresses are not allowed.")

    return url


def extract_website_content(url: str) -> dict:
    url = validate_url(url)

    headers = {
        "User-Agent": "InsightXAI/1.0"
    }

    try:
        with httpx.Client(
            timeout=15,
            follow_redirects=False,
            headers=headers
        ) as client:

            response = client.get(url)

            if response.is_redirect:
                raise ValueError(
                    "Website redirected. Please provide its final URL."
                )

            response.raise_for_status()

            content_type = response.headers.get("content-type", "")

            if "text/html" not in content_type.lower():
                raise ValueError("URL does not return an HTML page.")

            if len(response.content) > 2_000_000:
                raise ValueError("Website page is too large.")

            html = response.text

    except httpx.TimeoutException:
        raise ValueError("Website request timed out.")
    except httpx.HTTPStatusError as error:
        raise ValueError(
            f"Website returned HTTP {error.response.status_code}."
        )
    except httpx.RequestError:
        raise ValueError("Could not connect to the website.")

    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else ""

    description_tag = soup.find(
        "meta", attrs={"name": "description"}
    )

    description = (
        description_tag.get("content", "")
        if description_tag else ""
    )

    for element in soup([
        "script", "style", "noscript",
        "header", "footer", "nav", "svg"
    ]):
        element.decompose()

    headings = []

    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(" ", strip=True)

        if text:
            headings.append({
                "tag": tag.name,
                "text": text
            })

    paragraphs = []

    for tag in soup.find_all("p"):
        text = tag.get_text(" ", strip=True)

        if len(text) > 30:
            paragraphs.append(text)

    full_text = " ".join(paragraphs)
    full_text = full_text[:30000]

    return {
        "url": url,
        "title": title,
        "meta_description": description,
        "headings": headings[:50],
        "content": full_text
    }
