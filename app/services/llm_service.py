
import json
import time

from google import genai
from google.genai import errors

from app.config import settings
from app.schemas import WebsiteAnalysis


def analyze_website_with_gemini(website_data: dict) -> WebsiteAnalysis:

    if not settings.GEMINI_API_KEY:
        raise ValueError("Gemini API key is missing. Check your .env file.")

    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options={"timeout": 120000}
    )

    prompt = f"""
You are an expert website analyst and digital business consultant.

Analyze this website:

{json.dumps(website_data, indent=2)}

Provide:
1. Business summary.
2. Potential competitors. Never invent verified competitor URLs.
3. Exactly 5 relevant search queries with platform, intent and reason.
4. SEO recommendations with priority, area and reason.
5. Up to 5 services supported by website evidence.
6. Primary audience, secondary audience and audience needs.
7. Limitations and uncertain conclusions.

Rules:
- Use website evidence for factual claims.
- Clearly distinguish facts from inferences.
- Never invent statistics or facts.
- Return valid JSON matching the supplied schema.
"""

    interaction = None

    for attempt in range(3):
        try:
            print(f"Sending request to Gemini (attempt {attempt + 1}/3)...")

            interaction = client.interactions.create(
                model=settings.GEMINI_MODEL,
                input=prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": WebsiteAnalysis.model_json_schema()
                },
                timeout=180
            )

            break

        except Exception as error:

            error_message = str(error).lower()

            is_timeout = "timeout" in error_message
            is_temporary_api_error = (
                isinstance(error, errors.APIError)
                and error.code in (429, 500, 503, 504)
            )

            if not is_timeout and not is_temporary_api_error:
                raise

            if attempt == 2:
                raise

            wait_time = 2 ** (attempt + 1)

            print(
                f"Temporary Gemini error: {error}"
            )
            print(f"Retrying in {wait_time} seconds...")

            time.sleep(wait_time)

    if interaction is None:
        raise RuntimeError("Gemini could not complete the analysis.")

    if not interaction.output_text:
        raise ValueError("Gemini returned an empty response.")

    try:
        result = WebsiteAnalysis.model_validate_json(
            interaction.output_text
        )
    except Exception as error:
        raise ValueError(
            f"Gemini returned invalid analysis JSON: {error}"
        ) from error

    return result
