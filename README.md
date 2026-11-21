# Automated Multi-Platform Posting System

A FastAPI service that accepts one validated short message and publishes it to **six third-party platforms** in a single request. Each platform is integrated independently: a missing key, a rejected post or a timeout on one platform never stops the others.

> This repository also retains the earlier **AI link-analysis** utility (`app/services/website_extractor.py`, `app/services/llm_service.py`, `app/schemas.py` analysis models). The posting API was added alongside it and reuses the configured Gemini key.

---

## 1. Features

- `POST /posting` — one endpoint, server-side platform selection.
- Validation: message ≤ 200 characters, **exactly one** CTA link, public http/https URL only (localhost/private IPs rejected).
- Six real API integrations with per-platform results.
- Concurrent, isolated execution via `asyncio.gather`.
- Secrets loaded from environment variables; credentials are never echoed back (error strings are redacted).
- Automatic OpenAPI docs at `http://localhost:4000/docs`.
- 14 automated tests covering validation, isolation and the HTTP contract.

---

## 2. Project structure

```text
automated-posting/
├── app/
│   ├── main.py                     # FastAPI app + POST /posting
│   ├── config.py                   # Environment-based settings
│   ├── schemas.py                  # Request/response + existing analysis models
│   ├── platforms/
│   │   ├── base.py                 # BasePlatform, PostResult, error redaction
│   │   ├── gemini_platform.py      # LLM platform (Gemini)
│   │   ├── mastodon.py
│   │   ├── bluesky.py
│   │   ├── devto.py
│   │   ├── reddit.py
│   │   └── x_platform.py
│   ├── services/
│   │   ├── posting_service.py      # Concurrent orchestration
│   │   ├── website_extractor.py    # (pre-existing link-analysis feature)
│   │   └── llm_service.py          # (pre-existing link-analysis feature)
│   └── utils/
│       └── validators.py           # Link extraction + CTA validation
├── tests/
│   └── test_posting.py
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## 3. Platform research

| # | Platform | Official API documentation | Credentials (`.env`) | Public URL? |
|---|----------|----------------------------|----------------------|-------------|
| 1 | Gemini (LLM) | [Gemini API – generateContent](https://ai.google.dev/gemini-api/docs) | `GEMINI_API_KEY`, `GEMINI_MODEL` | **No** — accepts/processes the message; `posted_url=null`, `public_access=false` (honest reporting, no fabricated URL) |
| 2 | Mastodon | [POST /api/v1/statuses](https://docs.joinmastodon.org/methods/statuses/) | `MASTODON_BASE_URL`, `MASTODON_ACCESS_TOKEN` | Yes, `url` from the Status entity |
| 3 | Bluesky | [com.atproto.repo.createRecord](https://docs.bsky.app/docs/api/com-atproto-repo-create-record), [posting guide](https://docs.bsky.app/blog/create-post) | `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` | Yes, built from handle + record key |
| 4 | DEV Community | [Forem API – create article](https://developers.forem.com/api/v0) | `DEVTO_API_KEY` | Yes, `url` from the Article entity |
| 5 | Reddit | [Reddit API – /api/submit](https://www.reddit.com/dev/api/), [OAuth2](https://github.com/reddit-archive/reddit/wiki/OAuth2) | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`, `REDDIT_SUBREDDIT` | Yes, permalink from the submit response |
| 6 | X (Twitter) | [X API v2 – POST /2/tweets](https://docs.x.com/x-api/posts/manage-tweets/quickstart) | `X_BEARER_TOKEN` | Yes, `https://x.com/i/web/status/{id}` |

Notes:
- Bluesky requires an **app password**, not the account password.
- Reddit needs a registered *script* app; new apps/tokens may need Reddit approval.
- X requires an API plan with write access to `POST /2/tweets`.
- If a credential is absent, that adapter returns `Missing credentials: ...` and the other five are still attempted.

---

## 4. Setup

```bash
# Python 3.x is required (tested with Python 3.13)
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt

# Create your local configuration
copy .env.example .env        # Windows
cp .env.example .env          # macOS / Linux
```

Edit `.env` and fill in the credentials of the platforms you want to use. The Gemini key in the existing `.env` works out of the box; use a currently available model such as `gemini-3.5-flash-lite` (older models can return `404 NOT_FOUND` or `503 UNAVAILABLE`).

Start the server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Open the interactive docs: **http://localhost:4000/docs**

---

## 5. API usage

### Request

```bash
curl -X POST "http://localhost:4000/posting" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Check out our latest business platform and grow your online visibility. https://example.com\"}"
```

### Response (actual output from a live local run)

Gemini was configured; the other five platforms had no credentials, so they failed independently while the request still succeeded overall.

```json
{
  "success": true,
  "results": [
    {
      "platform": "Gemini (LLM)",
      "status": "success",
      "posted_url": null,
      "public_access": false,
      "date": "2026-11-22",
      "time": "00:08:27",
      "error": null
    },
    {
      "platform": "Mastodon",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Missing credentials: MASTODON_BASE_URL, MASTODON_ACCESS_TOKEN"
    },
    {
      "platform": "Bluesky",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Missing credentials: BLUESKY_HANDLE, BLUESKY_APP_PASSWORD"
    },
    {
      "platform": "DEV Community",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Missing credentials: DEVTO_API_KEY"
    },
    {
      "platform": "Reddit",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Missing credentials: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD"
    },
    {
      "platform": "X (Twitter)",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Missing credentials: X_BEARER_TOKEN"
    }
  ]
}
```

`success: true` means **at least one** platform accepted the message. With every credential configured, successful social platforms return a real `posted_url` and `public_access: true`.

### Validation errors (HTTP 422)

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "message"],
      "msg": "Value error, Message must include exactly one CTA link; found 2 links."
    }
  ]
}
```

Examples of rejected input: empty message, more than 200 characters, no link, two links, `https://`, `http://localhost:8000`, `http://192.168.1.10/admin`.

---

## 6. Testing

```bash
pytest -q
```

Actual result:

```text
..............                                                           [100%]
14 passed in 1.44s
```

Covered: valid/invalid messages, 422 response, failure isolation across platforms, credential-missing results, secret redaction, and the exact JSON response shape.

Server log from the live request:

```text
INFO:     Uvicorn running on http://127.0.0.1:4000 (Press CTRL+C to quit)
Mastodon skipped: credentials missing
Bluesky skipped: credentials missing
DEV Community skipped: credentials missing
Reddit skipped: credentials missing
X (Twitter) skipped: credentials missing
INFO:     127.0.0.1:55643 - "POST /posting HTTP/1.1" 200 OK
```

---

## 7. Security

- `.env` is listed in `.gitignore`; no keys are committed. Use `.env.example` as the template.
- Error strings pass through `sanitize_error()`, which removes known secret values and masks `Bearer` tokens.
- CTA validation rejects localhost/private addresses to reduce misuse as an SSRF-style target.
- No simulated or fabricated posted URLs are returned. When credentials are missing the API reports a real failure.

---

## 8. Submission checklist

- [x] Complete source code in this repository
- [x] `.env.example` with every required variable (no real values)
- [x] `README.md` with setup, execution, sample request/response and logs
- [x] Automated tests
- [ ] Add a screenshot of the Swagger docs (`/docs`) before submission
- [ ] Push to a **public** GitHub repository and email the link as instructed
