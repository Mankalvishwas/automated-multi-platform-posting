
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


class Settings:
    APP_NAME = os.getenv("APP_NAME", "InsightX AI")
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "30000"))

    # --- Multi-platform posting credentials -------------------------------
    # Gemini is already used by the link-analysis feature and doubles as the
    # supported LLM platform for the posting system.
    MASTODON_BASE_URL = os.getenv("MASTODON_BASE_URL", "")
    MASTODON_ACCESS_TOKEN = os.getenv("MASTODON_ACCESS_TOKEN", "")

    BLUESKY_SERVICE_URL = os.getenv(
        "BLUESKY_SERVICE_URL", "https://bsky.social"
    ).rstrip("/")
    BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE", "")
    BLUESKY_APP_PASSWORD = os.getenv("BLUESKY_APP_PASSWORD", "")

    DEVTO_API_KEY = os.getenv("DEVTO_API_KEY", "")

    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USERNAME = os.getenv("REDDIT_USERNAME", "")
    REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD", "")
    REDDIT_SUBREDDIT = os.getenv("REDDIT_SUBREDDIT", "test")

    X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")


# Create settings object
settings = Settings()