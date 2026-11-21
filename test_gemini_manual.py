
import json

from app.services.website_extractor import extract_website_content
from app.services.llm_service import analyze_website_with_gemini


url = "https://www.python.org"

try:
    print("1. Extracting website content...")

    website_data = extract_website_content(url)

    print("2. Sending website data to Gemini...")

    analysis = analyze_website_with_gemini(website_data)

    print("\nAI ANALYSIS SUCCESSFUL!")
    print("=" * 50)

    print(json.dumps(
        analysis.model_dump(),
        indent=4
    ))

except Exception as error:
    print("\nANALYSIS FAILED:")
    print(type(error).__name__, error)
