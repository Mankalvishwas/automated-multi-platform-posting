
from app.services.website_extractor import extract_website_content

url = "https://www.python.org"

try:
    result = extract_website_content(url)

    print("\nWEBSITE EXTRACTION SUCCESSFUL")
    print("Title:", result["title"])
    print("Description:", result["meta_description"])
    print("Headings:", result["headings"])
    print("Content:", result["content"][:500])

except Exception as error:
    print("ERROR:", error)